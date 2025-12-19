#!/usr/bin/env python3
"""
특정 위치에서 위치 추정 테스트 (시뮬레이션)
"""

from config import ARUBA_APS, ROOM_CENTROIDS, rssi_to_distance, get_nearest_room
from ble_scanner import SimulatedScanner
from position_estimator import PositionEstimator
import math

def test_at_position(x, y, room_name=""):
    """특정 위치에서 시뮬레이션 테스트"""
    print(f"\n{'='*60}")
    print(f"📍 테스트 위치: ({x:.1f}m, {y:.1f}m) - {room_name}")
    print("="*60)
    
    # 시뮬레이션 스캐너
    scanner = SimulatedScanner()
    scanner.set_position(x, y)
    
    # RSSI 스캔
    rssi_result = scanner.scan_sync()
    
    print("\n📶 예상 RSSI 값 (거리 기반 시뮬레이션):")
    print("-"*60)
    
    for ap_name in ["AP-12", "AP-11", "AP-XX", "AP-09", "AP-07", "AP-13"]:
        rssi = rssi_result[ap_name]
        ap_pos = ARUBA_APS[ap_name]["position"]
        distance = math.sqrt((x - ap_pos[0])**2 + (y - ap_pos[1])**2)
        
        # RSSI 바 그래프
        bar_len = max(0, int((rssi + 100) / 3))
        bar = "█" * bar_len
        
        print(f"  {ap_name:6} | {rssi:6.1f} dBm | 거리: {distance:5.1f}m | {bar}")
    
    # 위치 추정
    print("\n📍 위치 추정 결과:")
    print("-"*60)
    
    methods = ["weighted_centroid", "trilateration", "least_squares"]
    for method in methods:
        estimator = PositionEstimator(method=method)
        estimated = estimator.estimate(rssi_result)
        
        if estimated:
            error = math.sqrt((estimated[0] - x)**2 + (estimated[1] - y)**2)
            nearest = get_nearest_room(estimated[0], estimated[1])
            print(f"  {method:20} → ({estimated[0]:5.1f}m, {estimated[1]:5.1f}m) "
                  f"오차: {error:.1f}m, 근처 호실: {nearest}")
        else:
            print(f"  {method:20} → 추정 실패")

if __name__ == "__main__":
    print("\n" + "🔵"*30)
    print("  위치 추정 시뮬레이션 테스트")
    print("🔵"*30)
    
    # 7413 앞에서 테스트
    if "7413" in ROOM_CENTROIDS:
        x, y = ROOM_CENTROIDS["7413"]
        test_at_position(x, y, "7413 앞")
    else:
        # 7413 위치 추정 (7414와 7412 사이)
        test_at_position(9.1, 3.1, "7413 앞")
    
    # 다른 위치들도 테스트
    print("\n\n" + "="*60)
    print("📌 다른 위치 테스트")
    print("="*60)
    
    test_positions = [
        (5.0, 3.5, "AP-12 위치 (7415 근처)"),
        (25.3, 3.5, "AP-11 위치 (7411 앞)"),
        (38.2, 3.5, "AP-XX 위치 (7407-7408 중간)"),
        (47.3, 3.5, "AP-09 위치 (7405 앞)"),
        (58.7, 3.5, "AP-07 위치 (복도 끝)"),
    ]
    
    for x, y, desc in test_positions:
        test_at_position(x, y, desc)
