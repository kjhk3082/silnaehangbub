#!/usr/bin/env python3
"""
캘리브레이션 도구 (실시간 RSSI 표시)
"""

import json
import time
import threading
import sys
import os
from datetime import datetime

try:
    from CoreWLAN import CWWiFiClient
    client = CWWiFiClient.sharedWiFiClient()
    interface = client.interface()
    USE_WIFI = interface is not None
except:
    USE_WIFI = False

# 전역 변수
current_rssi = -50
running = True
calibration_data = []

def get_rssi():
    """현재 RSSI"""
    if not USE_WIFI or not interface:
        return -50
    return interface.rssiValue()

def rssi_monitor():
    """백그라운드에서 RSSI 실시간 업데이트"""
    global current_rssi, running
    
    while running:
        current_rssi = get_rssi()
        # 터미널 제목에 RSSI 표시
        sys.stdout.write(f"\033]0;📶 RSSI: {current_rssi} dBm\007")
        sys.stdout.flush()
        time.sleep(0.3)

def clear_line():
    """현재 줄 지우기"""
    sys.stdout.write('\r' + ' ' * 60 + '\r')
    sys.stdout.flush()

def main():
    global running, calibration_data, current_rssi
    
    print("\033[2J\033[H")  # 화면 클리어
    print("=" * 60)
    print("📐 캘리브레이션 도구 (실시간)")
    print("=" * 60)
    print(f"WiFi: {'✅ 연결됨' if USE_WIFI else '❌ 없음'}")
    print()
    print("사용법: 호실 앞에서 호실번호 입력 후 엔터")
    print("        'q' 입력하면 종료 & 저장")
    print("=" * 60)
    print()
    
    # RSSI 모니터 스레드 시작
    monitor_thread = threading.Thread(target=rssi_monitor, daemon=True)
    monitor_thread.start()
    
    try:
        while True:
            # 실시간 RSSI 표시
            print(f"\n📶 현재 RSSI: \033[96m{current_rssi}\033[0m dBm  (실시간 업데이트 중...)")
            
            # 입력 받기
            location = input("📍 위치 입력: ").strip()
            
            if location.lower() == 'q':
                break
            
            if not location:
                continue
            
            # 저장 시점의 RSSI
            rssi = current_rssi
            
            entry = {
                "location": location,
                "rssi": rssi,
                "timestamp": datetime.now().isoformat(),
                "time_str": datetime.now().strftime("%H:%M:%S")
            }
            calibration_data.append(entry)
            
            print(f"   \033[92m✅ 저장: {location} → {rssi} dBm\033[0m")
            print(f"   (총 {len(calibration_data)}개 기록)")
            
    except KeyboardInterrupt:
        pass
    finally:
        running = False
    
    # 결과 저장
    print("\n" + "=" * 60)
    print("📊 캘리브레이션 결과")
    print("=" * 60)
    
    if calibration_data:
        print(f"\n{'위치':<12} {'RSSI':<10} {'시간':<10}")
        print("-" * 35)
        for item in calibration_data:
            print(f"{item['location']:<12} {item['rssi']:<10} {item['time_str']:<10}")
        
        # JSON 저장
        os.makedirs("logs", exist_ok=True)
        filename = f"logs/calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output = {
            "created_at": datetime.now().isoformat(),
            "count": len(calibration_data),
            "data": calibration_data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 저장됨: {filename}")
    else:
        print("저장된 데이터 없음")

if __name__ == "__main__":
    main()
