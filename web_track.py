#!/usr/bin/env python3
"""
웹 기반 실시간 위치 추적
7413 = 원점 (0, 0)
"""

from flask import Flask, render_template, jsonify, request, send_file
import time
import json
import os
from datetime import datetime

# Fingerprinting 엔진 임포트
try:
    from fingerprint_engine import (
        scan_rssi_pattern, 
        collect_fingerprint,
        estimate_location_knn,
        fingerprint_db,
        add_fingerprint,
        load_db,
        save_db,
        get_db_stats
    )
    FINGERPRINT_AVAILABLE = True
except ImportError:
    FINGERPRINT_AVAILABLE = False
    print("⚠️ Fingerprint 엔진 로드 실패")

app = Flask(__name__)

# ============================================================
# WiFi 설정
# ============================================================
try:
    from CoreWLAN import CWWiFiClient
    client = CWWiFiClient.sharedWiFiClient()
    interface = client.interface()
    USE_WIFI = interface is not None
except:
    USE_WIFI = False
    interface = None

# ============================================================
# 캘리브레이션 (7413 = 0m)
# ============================================================
# 캘리브레이션 (7413 = 0m, 실측 기준 2025-12-19)
# 실측 데이터 기반 + 보정
CALIBRATION = [
    ("7413", -44,  0.0),    # 보정: -40~-44 범위 = 0m (7413 앞)
    ("7418", -54,  8.0),    # 실측: 계단/E/V 방향
    ("7419", -60,  12.0),   # 실측
    ("7420", -65,  18.0),   # 실측: 위쪽 복도 시작
    ("7422", -65,  28.0),   # 실측
    ("7423", -68,  38.0),   # 실측
    ("7424", -68,  48.0),   # 실측
    ("7404", -69,  55.0),   # 실측: 아래쪽 복도
    ("7429", -74,  65.0),   # 실측: 끝점
]

# 도면 기준 (7413 = 0m, EV쪽 벽 기준 순서)
# Fingerprint 수집 순서 기반: 7413 → STAIR → EV → 7412 → 7411 → ... → 7404
ROOM_POSITIONS = {
    # 시작점
    "7414": -5.0,
    "7413": 0.0,      # 원점
    # 시설 (EV쪽 벽 기준)
    "STAIR": 5.0,     # 계단
    "EV": 10.0,       # 엘리베이터
    # 아래쪽 복도 (EV 지나서)
    "7412": 15.0,
    "7411": 20.0,
    "7410": 25.0,
    "7409": 30.0,
    "7408": 35.0,
    "7407": 40.0,
    "7406": 45.0,
    "7405": 50.0,
    "7404": 55.0,
    "7403": 60.0,
    "7401": 65.0,
}

# 전역 데이터
tracking_data = {
    "active": False,
    "start_time": None,
    "trajectory": [],
    "current": None
}

# RSSI 평활화용 버퍼 (최근 N개 평균)
rssi_buffer = []
RSSI_BUFFER_SIZE = 10  # 더 많이 평균

# 위치 평활화용 버퍼
position_buffer = []
POSITION_BUFFER_SIZE = 8  # 더 많이 평균

# 이전 위치 (방향 감지용)
last_stable_position = 0
DIRECTION_THRESHOLD = 5.0  # 5m 이상 이동해야 방향 변경

# 위치 안정화 (작은 변화 무시)
MIN_POSITION_CHANGE = 1.0  # 1m 미만 변화는 무시
last_reported_position = 0

def rssi_to_position(rssi):
    """RSSI → 위치 (미터)"""
    rssi_list = [c[1] for c in CALIBRATION]
    pos_list = [c[2] for c in CALIBRATION]
    
    if rssi >= rssi_list[0]:
        return pos_list[0]
    elif rssi <= rssi_list[-1]:
        return pos_list[-1] + (rssi_list[-1] - rssi) * 1.0
    else:
        for i in range(len(rssi_list) - 1):
            if rssi_list[i] >= rssi >= rssi_list[i+1]:
                ratio = (rssi_list[i] - rssi) / (rssi_list[i] - rssi_list[i+1])
                return pos_list[i] + ratio * (pos_list[i+1] - pos_list[i])
    return 0

def get_nearest_room(pos):
    """위치에서 가장 가까운 호실"""
    min_dist = float('inf')
    nearest = "7413"
    for room, room_pos in ROOM_POSITIONS.items():
        dist = abs(pos - room_pos)
        if dist < min_dist:
            min_dist = dist
            nearest = room
    return nearest

# ============================================================
# API 엔드포인트
# ============================================================

@app.route('/')
def index():
    return render_template('track.html')

@app.route('/navi')
def navigation():
    """실내 네비게이션 페이지"""
    return render_template('navi.html')

@app.route('/analysis')
def analysis():
    """분석 및 시각화 페이지"""
    return render_template('analysis.html')

@app.route('/calibrate')
def calibrate_page():
    """캘리브레이션 페이지"""
    return render_template('calibrate.html')

@app.route('/api/calibration/save', methods=['POST'])
def save_calibration():
    """캘리브레이션 데이터 저장"""
    data = request.json
    
    os.makedirs("logs", exist_ok=True)
    filename = f"logs/calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    output = {
        "created_at": datetime.now().isoformat(),
        "count": len(data.get('data', [])),
        "data": data.get('data', [])
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    return jsonify({"status": "saved", "filename": filename})

# ============================================================
# Fingerprinting API
# ============================================================

@app.route('/fingerprint')
def fingerprint_page():
    """Fingerprint 수집 페이지"""
    return render_template('fingerprint.html')

@app.route('/api/fingerprint/scan')
def fingerprint_scan():
    """현재 RSSI 패턴 스캔"""
    if not FINGERPRINT_AVAILABLE:
        return jsonify({"error": "Fingerprint 엔진 없음"}), 500
    
    pattern = scan_rssi_pattern(15)
    return jsonify({
        "pattern": pattern,
        "count": len(pattern),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/fingerprint/collect', methods=['POST'])
def fingerprint_collect():
    """특정 위치에서 Fingerprint 수집"""
    if not FINGERPRINT_AVAILABLE:
        return jsonify({"error": "Fingerprint 엔진 없음"}), 500
    
    data = request.json
    location = data.get('location')
    samples = data.get('samples', 10)
    
    if not location:
        return jsonify({"error": "위치 필요"}), 400
    
    fingerprint = collect_fingerprint(location, samples=samples, top_n=15)
    
    if fingerprint:
        add_fingerprint(location, fingerprint)
        return jsonify({
            "status": "collected",
            "location": location,
            "pattern": fingerprint["pattern"],
            "samples": samples
        })
    else:
        return jsonify({"error": "수집 실패"}), 500

@app.route('/api/fingerprint/estimate')
def fingerprint_estimate():
    """현재 위치 추정 (Fingerprinting)"""
    if not FINGERPRINT_AVAILABLE:
        return jsonify({"error": "Fingerprint 엔진 없음"}), 500
    
    # 현재 패턴 스캔
    current_pattern = scan_rssi_pattern(15)
    
    if not current_pattern:
        return jsonify({"error": "스캔 실패"}), 500
    
    # 위치 추정
    location, confidence, top_k = estimate_location_knn(current_pattern, k=3)
    
    return jsonify({
        "estimated_location": location,
        "confidence": confidence,
        "current_pattern": current_pattern,
        "candidates": [
            {
                "location": item["location"],
                "distance": round(item["distance"], 2),
                "similarity": round(item["similarity"], 3)
            }
            for item in top_k
        ]
    })

@app.route('/api/fingerprint/db')
def fingerprint_db_info():
    """Fingerprint DB 정보"""
    if not FINGERPRINT_AVAILABLE:
        return jsonify({"error": "Fingerprint 엔진 없음"}), 500
    
    stats = get_db_stats()
    return jsonify(stats)

@app.route('/api/fingerprint/save', methods=['POST'])
def fingerprint_save():
    """Fingerprint 데이터 저장 (웹에서)"""
    if not FINGERPRINT_AVAILABLE:
        return jsonify({"error": "Fingerprint 엔진 없음"}), 500
    
    data = request.json
    
    # DB에 추가
    for location, fp_data in data.items():
        fingerprint_db[location] = {
            "location": location,
            "pattern": fp_data.get("pattern", []),
            "samples": len(fp_data.get("samples", [])),
            "avg": fp_data.get("avg"),
            "min": fp_data.get("min"),
            "max": fp_data.get("max"),
            "timestamp": datetime.now().isoformat()
        }
    
    save_db()
    
    return jsonify({
        "status": "saved",
        "filename": "logs/fingerprint_db.json",
        "count": len(fingerprint_db)
    })

@app.route('/api/status')
def get_status():
    """현재 상태 반환 (Fingerprinting 통합)"""
    global rssi_buffer, position_buffer, last_stable_position, last_reported_position
    
    raw_rssi = -50  # 기본값
    
    if USE_WIFI and interface:
        raw_rssi = interface.rssiValue()
    
    # RSSI 평활화 (이동 평균)
    rssi_buffer.append(raw_rssi)
    if len(rssi_buffer) > RSSI_BUFFER_SIZE:
        rssi_buffer.pop(0)
    
    smoothed_rssi = sum(rssi_buffer) / len(rssi_buffer)
    
    # ============================================================
    # Fingerprinting 기반 위치 추정 (우선)
    # ============================================================
    fp_location = None
    fp_confidence = 0
    fp_candidates = []
    
    if FINGERPRINT_AVAILABLE and len(fingerprint_db) >= 3:
        try:
            current_pattern = scan_rssi_pattern(15)
            if current_pattern:
                fp_location, fp_confidence, top_k = estimate_location_knn(current_pattern, k=3)
                fp_candidates = [
                    {"location": item["location"], "distance": round(item["distance"], 2)}
                    for item in top_k
                ]
        except:
            pass
    
    # ============================================================
    # 기존 RSSI 기반 위치 (fallback)
    # ============================================================
    raw_pos = rssi_to_position(smoothed_rssi)
    
    position_buffer.append(raw_pos)
    if len(position_buffer) > POSITION_BUFFER_SIZE:
        position_buffer.pop(0)
    
    smoothed_pos = sum(position_buffer) / len(position_buffer)
    
    if abs(smoothed_pos - last_reported_position) < MIN_POSITION_CHANGE:
        rssi_pos = last_reported_position
    else:
        rssi_pos = smoothed_pos
        last_reported_position = smoothed_pos
    
    rssi_room = get_nearest_room(rssi_pos)
    
    # ============================================================
    # 최종 위치 결정 (Fingerprint 우선, 높은 신뢰도만)
    # ============================================================
    # 신뢰도 0.75 이상일 때만 Fingerprint 사용, 그 외는 RSSI fallback
    if fp_location and fp_confidence >= 0.75:
        final_room = fp_location
        final_pos = ROOM_POSITIONS.get(fp_location, rssi_pos)
        method = "fingerprint"
    else:
        final_room = rssi_room
        final_pos = rssi_pos
        method = "rssi"
    
    # 방향 감지
    diff = final_pos - last_stable_position
    if abs(diff) >= DIRECTION_THRESHOLD:
        direction = "forward" if diff > 0 else "backward"
        last_stable_position = final_pos
    else:
        direction = "stay"
    
    # 추적 중이면 궤적에 추가
    if tracking_data["active"]:
        elapsed = time.time() - tracking_data["start_time"]
        point = {
            "time": round(elapsed, 1),
            "rssi": round(smoothed_rssi),
            "position": round(final_pos, 1),
            "room": final_room,
            "method": method,
            "confidence": round(fp_confidence, 2) if method == "fingerprint" else None
        }
        tracking_data["trajectory"].append(point)
        tracking_data["current"] = point
    
    return jsonify({
        "wifi_available": USE_WIFI,
        "rssi": round(smoothed_rssi),
        "raw_rssi": raw_rssi,
        "position": round(final_pos, 1),
        "room": final_room,
        "direction": direction,
        "method": method,
        "fingerprint": {
            "available": FINGERPRINT_AVAILABLE and len(fingerprint_db) >= 3,
            "location": fp_location,
            "confidence": round(fp_confidence, 2),
            "candidates": fp_candidates
        },
        "rssi_fallback": {
            "position": round(rssi_pos, 1),
            "room": rssi_room
        },
        "tracking": tracking_data["active"],
        "trajectory_count": len(tracking_data["trajectory"])
    })

@app.route('/api/start')
def start_tracking():
    """추적 시작"""
    tracking_data["active"] = True
    tracking_data["start_time"] = time.time()
    tracking_data["trajectory"] = []
    return jsonify({"status": "started"})

@app.route('/api/stop')
def stop_tracking():
    """추적 중지"""
    tracking_data["active"] = False
    return jsonify({
        "status": "stopped",
        "trajectory": tracking_data["trajectory"]
    })

@app.route('/api/trajectory')
def get_trajectory():
    """궤적 데이터 반환"""
    return jsonify({
        "trajectory": tracking_data["trajectory"],
        "rooms": ROOM_POSITIONS
    })

@app.route('/api/clear')
def clear_trajectory():
    """궤적 초기화"""
    tracking_data["trajectory"] = []
    return jsonify({"status": "cleared"})

@app.route('/api/save', methods=['POST'])
def save_trajectory():
    """궤적 JSON 저장"""
    os.makedirs("logs", exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"logs/track_{timestamp}.json"
    
    # 통계 계산
    traj = tracking_data["trajectory"]
    if traj:
        positions = [p['position'] for p in traj]
        rooms_visited = list(dict.fromkeys([p['room'] for p in traj]))
        stats = {
            "min_position": min(positions),
            "max_position": max(positions),
            "total_distance": max(positions) - min(positions),
            "rooms_visited": rooms_visited,
            "point_count": len(traj)
        }
    else:
        stats = {}
    
    data = {
        "saved_at": datetime.now().isoformat(),
        "origin": "7413",
        "duration_sec": traj[-1]['time'] if traj else 0,
        "stats": stats,
        "trajectory": traj
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return jsonify({
        "status": "saved",
        "filename": filename,
        "stats": stats
    })

@app.route('/api/list')
def list_saved():
    """저장된 파일 목록"""
    os.makedirs("logs", exist_ok=True)
    files = []
    for f in os.listdir("logs"):
        if f.startswith("track_") and f.endswith(".json"):
            path = os.path.join("logs", f)
            files.append({
                "filename": f,
                "path": path,
                "size": os.path.getsize(path),
                "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
            })
    files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({"files": files})

@app.route('/api/load/<filename>')
def load_trajectory(filename):
    """저장된 궤적 불러오기"""
    path = os.path.join("logs", filename)
    if not os.path.exists(path):
        return jsonify({"error": "파일 없음"}), 404
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return jsonify(data)

@app.route('/api/download/<filename>')
def download_trajectory(filename):
    """JSON 파일 다운로드"""
    path = os.path.join("logs", filename)
    if not os.path.exists(path):
        return jsonify({"error": "파일 없음"}), 404
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    print("=" * 60)
    print("🌐 웹 기반 실시간 위치 추적")
    print("=" * 60)
    print(f"WiFi 사용: {'✅ 가능' if USE_WIFI else '❌ 불가'}")
    print("\n🔗 http://localhost:5001 에서 확인하세요!")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5001, threaded=True)
