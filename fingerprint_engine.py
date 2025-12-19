#!/usr/bin/env python3
"""
WiFi Fingerprinting Engine
RSSI 패턴 기반 실내 위치 추정
"""

import json
import os
import math
from datetime import datetime
from collections import defaultdict

try:
    from CoreWLAN import CWWiFiClient
    client = CWWiFiClient.sharedWiFiClient()
    interface = client.interface()
    USE_WIFI = interface is not None
except:
    USE_WIFI = False
    interface = None

# Fingerprint 데이터베이스
fingerprint_db = {}
DB_FILE = "logs/fingerprint_db.json"

def scan_rssi_pattern(top_n=10):
    """
    주변 AP들의 RSSI 패턴 스캔
    상위 N개 RSSI를 정렬된 벡터로 반환
    """
    if not USE_WIFI or not interface:
        return []
    
    try:
        # 스캔 실행
        networks, error = interface.scanForNetworksWithSSID_error_(None, None)
        
        if not networks:
            # 캐시 사용
            networks = interface.cachedScanResults() or []
        
        # RSSI 값만 추출
        rssi_list = []
        for network in networks:
            rssi = network.rssiValue()
            if rssi and rssi > -100:  # 유효한 값만
                rssi_list.append(rssi)
        
        # 정렬 (강한 신호부터)
        rssi_list.sort(reverse=True)
        
        # 상위 N개 반환
        return rssi_list[:top_n]
    
    except Exception as e:
        print(f"스캔 에러: {e}")
        return []

def collect_fingerprint(location, samples=10, top_n=10):
    """
    특정 위치에서 Fingerprint 수집
    여러 번 스캔해서 평균 패턴 생성
    """
    all_patterns = []
    
    for i in range(samples):
        pattern = scan_rssi_pattern(top_n)
        if pattern:
            all_patterns.append(pattern)
        import time
        time.sleep(0.3)
    
    if not all_patterns:
        return None
    
    # 평균 패턴 계산
    avg_pattern = []
    for i in range(top_n):
        values = [p[i] for p in all_patterns if i < len(p)]
        if values:
            avg_pattern.append(round(sum(values) / len(values)))
    
    # 통계
    fingerprint = {
        "location": location,
        "pattern": avg_pattern,
        "samples": samples,
        "timestamp": datetime.now().isoformat(),
        "raw_patterns": all_patterns
    }
    
    return fingerprint

def euclidean_distance(pattern1, pattern2):
    """유클리드 거리 계산"""
    if not pattern1 or not pattern2:
        return float('inf')
    
    # 길이 맞추기
    min_len = min(len(pattern1), len(pattern2))
    
    sum_sq = 0
    for i in range(min_len):
        sum_sq += (pattern1[i] - pattern2[i]) ** 2
    
    return math.sqrt(sum_sq)

def cosine_similarity(pattern1, pattern2):
    """코사인 유사도 계산"""
    if not pattern1 or not pattern2:
        return 0
    
    min_len = min(len(pattern1), len(pattern2))
    
    dot_product = sum(pattern1[i] * pattern2[i] for i in range(min_len))
    norm1 = math.sqrt(sum(x**2 for x in pattern1[:min_len]))
    norm2 = math.sqrt(sum(x**2 for x in pattern2[:min_len]))
    
    if norm1 == 0 or norm2 == 0:
        return 0
    
    return dot_product / (norm1 * norm2)

def estimate_location_knn(current_pattern, k=3):
    """
    KNN 알고리즘으로 위치 추정
    가장 유사한 K개 위치의 가중 평균
    """
    if not fingerprint_db or not current_pattern:
        return None, 0, []
    
    # 각 위치와의 거리 계산
    distances = []
    for location, data in fingerprint_db.items():
        stored_pattern = data.get("pattern", [])
        dist = euclidean_distance(current_pattern, stored_pattern)
        similarity = cosine_similarity(current_pattern, stored_pattern)
        distances.append({
            "location": location,
            "distance": dist,
            "similarity": similarity,
            "pattern": stored_pattern
        })
    
    # 거리순 정렬
    distances.sort(key=lambda x: x["distance"])
    
    # 상위 K개
    top_k = distances[:k]
    
    if not top_k:
        return None, 0, []
    
    # 가장 가까운 위치
    best_match = top_k[0]
    
    # 신뢰도 계산 (거리 기반)
    if best_match["distance"] < 5:
        confidence = 0.95
    elif best_match["distance"] < 10:
        confidence = 0.8
    elif best_match["distance"] < 20:
        confidence = 0.6
    else:
        confidence = 0.3
    
    return best_match["location"], confidence, top_k

def load_db():
    """Fingerprint DB 로드"""
    global fingerprint_db
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                fingerprint_db = json.load(f)
            print(f"✅ DB 로드: {len(fingerprint_db)}개 위치")
        except:
            fingerprint_db = {}
    
    return fingerprint_db

def save_db():
    """Fingerprint DB 저장"""
    os.makedirs("logs", exist_ok=True)
    
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(fingerprint_db, f, indent=2, ensure_ascii=False)
    
    print(f"✅ DB 저장: {len(fingerprint_db)}개 위치")

def add_fingerprint(location, fingerprint):
    """DB에 Fingerprint 추가"""
    fingerprint_db[location] = fingerprint
    save_db()

def get_db_stats():
    """DB 통계"""
    if not fingerprint_db:
        return {"count": 0, "locations": []}
    
    return {
        "count": len(fingerprint_db),
        "locations": list(fingerprint_db.keys()),
        "total_samples": sum(fp.get("samples", 0) for fp in fingerprint_db.values())
    }

# 초기화 시 DB 로드
load_db()

# ============================================================
# 테스트
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("📍 WiFi Fingerprinting Engine 테스트")
    print("=" * 60)
    
    # 현재 패턴 스캔
    print("\n🔍 현재 RSSI 패턴 스캔...")
    pattern = scan_rssi_pattern(10)
    print(f"   패턴: {pattern}")
    
    # DB 상태
    stats = get_db_stats()
    print(f"\n📊 DB 상태: {stats['count']}개 위치")
    
    if stats['count'] > 0:
        # 위치 추정
        print("\n🎯 위치 추정 중...")
        location, confidence, top_k = estimate_location_knn(pattern)
        
        if location:
            print(f"   추정 위치: {location} (신뢰도: {confidence*100:.0f}%)")
            print(f"   Top-3 후보:")
            for item in top_k:
                print(f"     - {item['location']}: 거리={item['distance']:.1f}, 유사도={item['similarity']:.2f}")
    else:
        print("\n⚠️ DB가 비어있습니다. 먼저 Fingerprint를 수집하세요!")
