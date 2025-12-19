#!/usr/bin/env python3
"""
복도 걸으면서 AP 수집
연결된 AP가 바뀔 때마다 자동 기록
"""

import time
import json
from datetime import datetime
from CoreWLAN import CWWiFiClient

# 수집된 AP 저장
collected_aps = {}
trajectory = []

def normalize_mac(mac):
    if not mac:
        return ""
    mac = mac.upper().replace("-", ":").replace(".", ":")
    mac_clean = mac.replace(":", "")
    if len(mac_clean) == 12:
        return ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))
    return mac

print("=" * 70)
print("🚶 복도 걸으면서 AP 수집")
print("=" * 70)
print("\n📌 사용법:")
print("   1. 복도를 천천히 걸어가세요")
print("   2. AP가 바뀌면 자동으로 기록됩니다")
print("   3. 호실 앞에서 잠시 멈추고 Enter를 누르면 위치 기록")
print("   4. 'q' + Enter로 종료")
print("\n" + "=" * 70)

client = CWWiFiClient.sharedWiFiClient()
interface = client.interface()

if not interface:
    print("❌ WiFi 인터페이스 없음")
    exit(1)

print(f"✅ WiFi 인터페이스: {interface.interfaceName()}")
print("\n🎬 수집 시작! (Ctrl+C 또는 'q'로 종료)\n")

last_bssid = None
start_time = time.time()
count = 0

try:
    while True:
        # 현재 연결 정보
        ssid = interface.ssid()
        bssid = normalize_mac(interface.bssid() or "")
        rssi = interface.rssiValue()
        channel = interface.wlanChannel()
        ch_num = channel.channelNumber() if channel else 0
        
        current_time = time.time() - start_time
        
        if ssid and bssid:
            # AP가 바뀌었는지 확인
            if bssid != last_bssid:
                count += 1
                print(f"\n{'🆕' if bssid not in collected_aps else '📍'} [{count}] AP 변경 감지! (t={current_time:.1f}s)")
                print(f"   BSSID: {bssid}")
                print(f"   SSID: {ssid}")
                print(f"   RSSI: {rssi} dBm")
                print(f"   채널: {ch_num}")
                
                # 저장
                if bssid not in collected_aps:
                    collected_aps[bssid] = {
                        "ssid": ssid,
                        "first_seen": current_time,
                        "rssi_samples": [rssi],
                        "channel": ch_num,
                        "location_hint": None
                    }
                    print(f"   ✨ 새로운 AP 발견!")
                else:
                    collected_aps[bssid]["rssi_samples"].append(rssi)
                    print(f"   📝 기존 AP 재접속")
                
                trajectory.append({
                    "time": current_time,
                    "bssid": bssid,
                    "rssi": rssi
                })
                
                last_bssid = bssid
                
                # 위치 힌트 입력 받기
                print(f"\n   💡 현재 위치(호실번호) 입력 (Enter=스킵, q=종료): ", end="", flush=True)
            
            # 주기적 상태 출력
            else:
                # RSSI 샘플 추가
                if bssid in collected_aps:
                    collected_aps[bssid]["rssi_samples"].append(rssi)
        
        # 비동기 입력 체크 (타임아웃 없이)
        import select
        import sys
        
        if select.select([sys.stdin], [], [], 0.5)[0]:
            user_input = sys.stdin.readline().strip()
            if user_input.lower() == 'q':
                break
            elif user_input and bssid:
                collected_aps[bssid]["location_hint"] = user_input
                print(f"   ✅ 위치 기록: {user_input}")
        
        time.sleep(0.5)
        
except KeyboardInterrupt:
    print("\n\n⏹️ 수집 중단")

# 결과 출력
print("\n" + "=" * 70)
print("📊 수집 결과")
print("=" * 70)

print(f"\n발견된 AP: {len(collected_aps)}개")
print(f"총 시간: {time.time() - start_time:.1f}초")
print(f"AP 변경 횟수: {count}회")

print("\n📡 발견된 AP 목록:")
print("-" * 70)
for bssid, info in collected_aps.items():
    avg_rssi = sum(info["rssi_samples"]) / len(info["rssi_samples"])
    loc = info["location_hint"] or "미입력"
    print(f"  {bssid}")
    print(f"    SSID: {info['ssid']}")
    print(f"    채널: {info['channel']}")
    print(f"    평균 RSSI: {avg_rssi:.1f} dBm ({len(info['rssi_samples'])}샘플)")
    print(f"    위치 힌트: {loc}")
    print()

# JSON 저장
output = {
    "timestamp": datetime.now().isoformat(),
    "duration_sec": time.time() - start_time,
    "aps": collected_aps,
    "trajectory": trajectory
}

filename = f"logs/walk_collect_{datetime.now().strftime('%H%M%S')}.json"
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"💾 저장됨: {filename}")

# config.py에 추가할 코드 출력
print("\n" + "=" * 70)
print("📝 config.py에 추가할 AP 정보:")
print("-" * 70)
for bssid, info in collected_aps.items():
    loc = info["location_hint"] or "unknown"
    print(f'    "{bssid}": "AP-{loc}",  # {info["ssid"]}')
