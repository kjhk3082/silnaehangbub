"""
Flask 웹 애플리케이션
실시간 위치 추적 및 궤적 시각화
"""

import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from config import ARUBA_APS, AP_POSITIONS, MAP_BOUNDS, rssi_to_distance, LOG_FILE
from ble_scanner import ArubaBLEScanner, SimulatedScanner
from position_estimator import PositionEstimator

app = Flask(__name__)
CORS(app)

# 전역 변수
scanner = None
estimator = None
trajectory = []
current_position = None
is_tracking = False
use_simulation = True  # 시뮬레이션 모드 기본 활성화

# 백그라운드 스캔 스레드
scan_thread = None
stop_scanning = False


def init_scanner():
    """스캐너 초기화"""
    global scanner, estimator
    
    if use_simulation:
        scanner = SimulatedScanner()
        print("📌 시뮬레이션 모드로 실행")
    else:
        scanner = ArubaBLEScanner()
        print("📡 실제 BLE 스캔 모드로 실행")
    
    estimator = PositionEstimator(method="weighted_centroid")


def background_scan():
    """백그라운드 스캔 루프"""
    global current_position, trajectory, stop_scanning
    
    while not stop_scanning:
        if is_tracking:
            try:
                # RSSI 스캔
                rssi_result = scanner.scan_sync(duration=1.5)
                
                # 위치 추정
                position = estimator.estimate(rssi_result)
                
                if position:
                    current_position = {
                        "x": position[0],
                        "y": position[1],
                        "timestamp": time.time(),
                        "datetime": datetime.now().isoformat()
                    }
                    
                    # 궤적에 추가
                    trajectory.append(current_position.copy())
                    
                    # 로그 저장
                    save_log()
                    
            except Exception as e:
                print(f"❌ 스캔 오류: {e}")
        
        time.sleep(0.5)


def save_log():
    """위치 로그 저장"""
    try:
        data = {
            "last_update": datetime.now().isoformat(),
            "ap_count": len(ARUBA_APS),
            "trajectory_count": len(trajectory),
            "trajectory": trajectory[-100:]  # 최근 100개만 저장
        }
        
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"로그 저장 오류: {e}")


@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """시스템 상태"""
    return jsonify({
        "is_tracking": is_tracking,
        "use_simulation": use_simulation,
        "ap_count": len(ARUBA_APS),
        "trajectory_count": len(trajectory)
    })


@app.route('/api/aps')
def get_aps():
    """AP 정보"""
    aps = []
    for name, info in ARUBA_APS.items():
        aps.append({
            "name": name,
            "location": info["location"],
            "ble_mac": info["ble_mac"],
            "position": {"x": info["position"][0], "y": info["position"][1]},
            "description": info["description"]
        })
    return jsonify(aps)


@app.route('/api/position')
def get_position():
    """현재 위치"""
    if current_position:
        return jsonify({
            "success": True,
            "position": current_position
        })
    return jsonify({
        "success": False,
        "message": "위치 정보 없음"
    })


@app.route('/api/trajectory')
def get_trajectory():
    """궤적 데이터"""
    return jsonify({
        "count": len(trajectory),
        "trajectory": trajectory[-200:]  # 최근 200개
    })


@app.route('/api/start', methods=['POST'])
def start_tracking():
    """추적 시작"""
    global is_tracking
    is_tracking = True
    return jsonify({"success": True, "message": "추적 시작"})


@app.route('/api/stop', methods=['POST'])
def stop_tracking():
    """추적 중지"""
    global is_tracking
    is_tracking = False
    return jsonify({"success": True, "message": "추적 중지"})


@app.route('/api/clear', methods=['POST'])
def clear_trajectory():
    """궤적 초기화"""
    global trajectory, current_position
    trajectory = []
    current_position = None
    return jsonify({"success": True, "message": "궤적 초기화됨"})


@app.route('/api/mode', methods=['POST'])
def set_mode():
    """모드 변경 (시뮬레이션/실제)"""
    global use_simulation, scanner
    
    data = request.get_json()
    use_simulation = data.get('simulation', True)
    
    # 스캐너 재초기화
    init_scanner()
    
    return jsonify({
        "success": True, 
        "mode": "simulation" if use_simulation else "real"
    })


@app.route('/api/simulate_move', methods=['POST'])
def simulate_move():
    """시뮬레이션 모드에서 위치 이동"""
    global current_position, trajectory
    
    if not use_simulation:
        return jsonify({"success": False, "message": "시뮬레이션 모드가 아닙니다"})
    
    data = request.get_json()
    x = data.get('x', 35)
    y = data.get('y', 5)
    
    # 시뮬레이션 스캐너 위치 설정
    scanner.set_position(x, y)
    
    # RSSI 스캔 및 위치 추정
    rssi_result = scanner.scan_sync()
    position = estimator.estimate(rssi_result)
    
    if position:
        current_position = {
            "x": position[0],
            "y": position[1],
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat()
        }
        trajectory.append(current_position.copy())
        
        return jsonify({
            "success": True,
            "position": current_position,
            "rssi": rssi_result
        })
    
    return jsonify({"success": False, "message": "위치 추정 실패"})


@app.route('/api/map_bounds')
def get_map_bounds():
    """맵 경계 정보"""
    return jsonify(MAP_BOUNDS)


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Aruba AP 실내 위치 추적 시스템")
    print("=" * 60)
    
    # 스캐너 초기화
    init_scanner()
    
    # 백그라운드 스캔 스레드 시작
    scan_thread = threading.Thread(target=background_scan, daemon=True)
    scan_thread.start()
    
    print("\n📡 서버 시작: http://localhost:5000")
    print("📌 시뮬레이션 모드로 실행됩니다")
    print("   (실제 BLE 스캔은 mode API로 변경)")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
