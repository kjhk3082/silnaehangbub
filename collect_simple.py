#!/usr/bin/env python3
"""
간단한 AP 수집 - 1초마다 현재 AP 출력
"""

import time
import json
from datetime import datetime

try:
    from CoreWLAN import CWWiFiClient
except:
    print("❌ CoreWLAN 없음. pip install pyobjc-framework-CoreWLAN")
    exit(1)

def normalize_mac(mac):
    if not mac:
        return ""
    mac = mac.upper().replace("-", ":").replace(".", ":")
    mac_clean = mac.replace(":", "")
    if len(mac_clean) == 12:
        return ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))
    return mac

print("=" * 60)
print("🚶 AP 수집 - 복도 걸으면서 실행")
print("=" * 60)
print("Ctrl+C로 종료\n")

client = CWWiFiClient.sharedWiFiClient()
interface = client.interface()

if not interface:
    print("❌ WiFi 없음")
    exit(1)

collected = {}
last_bssid = None
start = time.time()

try:
    while True:
        bssid = normalize_mac(interface.bssid() or "")
        rssi = interface.rssiValue()
        ssid = interface.ssid() or ""
        
        t = time.time() - start
        
        if bssid and bssid != last_bssid:
            marker = "🆕 새 AP!" if bssid not in collected else "📍 재연결"
            print(f"\n[{t:5.1f}s] {marker}")
            print(f"        BSSID: {bssid}")
            print(f"        RSSI: {rssi} dBm")
            
            if bssid not in collected:
                collected[bssid] = {"rssi": [], "first": t}
            collected[bssid]["rssi"].append(rssi)
            collected[bssid]["last"] = t
            
            last_bssid = bssid
        elif bssid:
            # 같은 AP - RSSI만 업데이트
            if bssid in collected:
                collected[bssid]["rssi"].append(rssi)
            print(f"\r[{t:5.1f}s] {bssid} | RSSI: {rssi} dBm    ", end="", flush=True)
        
        time.sleep(1)

except KeyboardInterrupt:
    pass

# 결과
print("\n\n" + "=" * 60)
print(f"📊 결과: {len(collected)}개 AP 발견")
print("=" * 60)

for bssid, info in collected.items():
    avg = sum(info["rssi"]) / len(info["rssi"])
    print(f"\n{bssid}")
    print(f"  평균 RSSI: {avg:.0f} dBm")
    print(f"  구간: {info['first']:.0f}s ~ {info['last']:.0f}s")

# 저장
filename = f"logs/aps_{datetime.now().strftime('%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(collected, f, indent=2)
print(f"\n💾 저장: {filename}")
