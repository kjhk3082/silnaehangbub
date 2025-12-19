#!/usr/bin/env python3
"""
Aruba AP 기반 실내 위치 추적 시스템
메인 실행 스크립트
"""

import sys
import time
import json
import argparse
from datetime import datetime

from config import ARUBA_APS, print_ap_info
from ble_scanner import ArubaBLEScanner, SimulatedScanner
from position_estimator import PositionEstimator
from map_visualizer import MapVisualizer, create_static_map


def run_console_mode(simulation: bool = True, duration: int = 60):
    """
    콘솔 모드로 위치 추적 실행
    
    Args:
        simulation: 시뮬레이션 모드 여부
        duration: 실행 시간 (초)
    """
    print("\n" + "=" * 60)
    print("📡 Aruba AP 실내 위치 추적 - 콘솔 모드")
    print("=" * 60)
    
    # 스캐너 초기화
    if simulation:
        print("📌 시뮬레이션 모드로 실행")
        scanner = SimulatedScanner()
    else:
        print("📡 실제 BLE 스캔 모드로 실행")
        scanner = ArubaBLEScanner()
    
    # 위치 추정기 초기화
    estimator = PositionEstimator(method="weighted_centroid")
    
    # 궤적 데이터
    trajectory = []
    
    print(f"\n⏱️ {duration}초 동안 위치 추적 시작...")
    print("   (Ctrl+C로 중지)\n")
    
    start_time = time.time()
    scan_count = 0
    
    try:
        while time.time() - start_time < duration:
            scan_count += 1
            print(f"\n[스캔 #{scan_count}] {datetime.now().strftime('%H:%M:%S')}")
            
            # 시뮬레이션 모드에서는 랜덤 이동
            if simulation:
                import random
                x = 10 + (scan_count * 3) % 60
                y = 5 + random.uniform(-1.5, 1.5)
                scanner.set_position(x, y)
            
            # RSSI 스캔
            rssi_result = scanner.scan_sync(duration=1.5)
            
            # RSSI 출력
            print("  📶 RSSI 값:")
            for ap, rssi in sorted(rssi_result.items(), key=lambda x: x[1], reverse=True):
                bar = "█" * max(0, int((rssi + 100) / 5))
                print(f"     {ap}: {rssi:.1f} dBm {bar}")
            
            # 위치 추정
            position = estimator.estimate(rssi_result)
            
            if position:
                print(f"\n  📍 추정 위치: ({position[0]:.2f}m, {position[1]:.2f}m)")
                
                trajectory.append({
                    "x": position[0],
                    "y": position[1],
                    "timestamp": time.time()
                })
            else:
                print("\n  ⚠️ 위치 추정 실패")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ 사용자에 의해 중지됨")
    
    # 결과 저장
    print(f"\n📊 결과 요약:")
    print(f"   - 총 스캔 횟수: {scan_count}")
    print(f"   - 궤적 포인트: {len(trajectory)}개")
    
    if trajectory:
        # JSON 저장
        output_file = f"logs/trajectory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "simulation": simulation,
                "scan_count": scan_count,
                "trajectory": trajectory
            }, f, indent=2, ensure_ascii=False)
        print(f"   - 궤적 데이터 저장: {output_file}")
        
        # 맵 생성
        trajectory_points = [(p["x"], p["y"]) for p in trajectory]
        map_file = f"logs/trajectory_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        create_static_map(trajectory_points, map_file)
        print(f"   - 궤적 맵 저장: {map_file}")


def run_web_mode():
    """웹 서버 모드로 실행"""
    print("\n" + "=" * 60)
    print("🌐 Aruba AP 실내 위치 추적 - 웹 모드")
    print("=" * 60)
    print("\n웹 서버를 시작합니다...")
    
    # app.py 실행
    from app import app, init_scanner, background_scan
    import threading
    
    init_scanner()
    
    # 백그라운드 스캔 스레드
    scan_thread = threading.Thread(target=background_scan, daemon=True)
    scan_thread.start()
    
    print("\n📡 서버 주소: http://localhost:5000")
    print("   브라우저에서 위 주소로 접속하세요.")
    print("   (Ctrl+C로 종료)\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)


def run_test():
    """시스템 테스트"""
    print("\n" + "=" * 60)
    print("🧪 시스템 테스트")
    print("=" * 60)
    
    # AP 정보 출력
    print_ap_info()
    
    # 스캐너 테스트
    print("\n1️⃣ 시뮬레이션 스캐너 테스트")
    scanner = SimulatedScanner()
    scanner.set_position(35, 5)
    rssi = scanner.scan_sync()
    print("   RSSI 결과:")
    for ap, val in rssi.items():
        print(f"     {ap}: {val:.1f} dBm")
    
    # 위치 추정 테스트
    print("\n2️⃣ 위치 추정 테스트")
    estimator = PositionEstimator(method="weighted_centroid")
    position = estimator.estimate(rssi)
    if position:
        print(f"   추정 위치: ({position[0]:.2f}m, {position[1]:.2f}m)")
        print(f"   실제 위치: (35.00m, 5.00m)")
        error = ((position[0] - 35)**2 + (position[1] - 5)**2) ** 0.5
        print(f"   오차: {error:.2f}m")
    
    # 맵 시각화 테스트
    print("\n3️⃣ 맵 시각화 테스트")
    try:
        visualizer = MapVisualizer()
        visualizer.setup_map()
        visualizer.update_position(35, 5)
        visualizer.save("logs/test_map.png")
        print("   테스트 맵 저장됨: logs/test_map.png")
    except Exception as e:
        print(f"   시각화 오류: {e}")
    
    print("\n✅ 모든 테스트 완료!")


def main():
    parser = argparse.ArgumentParser(
        description="Aruba AP 기반 실내 위치 추적 시스템"
    )
    parser.add_argument(
        'mode',
        choices=['web', 'console', 'test'],
        nargs='?',
        default='web',
        help='실행 모드 (web/console/test)'
    )
    parser.add_argument(
        '--simulation', '-s',
        action='store_true',
        default=True,
        help='시뮬레이션 모드 사용'
    )
    parser.add_argument(
        '--real', '-r',
        action='store_true',
        help='실제 BLE 스캔 모드 사용'
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=60,
        help='콘솔 모드 실행 시간 (초)'
    )
    
    args = parser.parse_args()
    
    # 실제 모드 옵션
    simulation = not args.real
    
    print("\n" + "🔵" * 30)
    print("  Aruba AP 실내 위치 추적 시스템")
    print("  Indoor Positioning with Aruba AP BLE")
    print("🔵" * 30)
    
    if args.mode == 'web':
        run_web_mode()
    elif args.mode == 'console':
        run_console_mode(simulation=simulation, duration=args.duration)
    elif args.mode == 'test':
        run_test()


if __name__ == "__main__":
    main()
