#!/usr/bin/env python3
"""
모든 WiFi AP 스캔 (디버그용)
"""

from CoreWLAN import CWWiFiClient

def normalize_mac(mac: str) -> str:
    """MAC 주소 정규화"""
    if not mac:
        return ""
    mac = mac.upper().replace("-", ":").replace(".", ":")
    mac_clean = mac.replace(":", "")
    if len(mac_clean) == 12:
        return ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))
    return mac

print("=" * 80)
print("📡 전체 WiFi AP 스캔")
print("=" * 80)

client = CWWiFiClient.sharedWiFiClient()
interface = client.interface()

if not interface:
    print("❌ WiFi 인터페이스 없음")
    exit(1)

print(f"✅ 인터페이스: {interface.interfaceName()}")
print(f"   현재 연결: {interface.ssid() or '없음'}")
print()

# 스캔
networks, error = interface.scanForNetworksWithName_error_(None, None)

if error:
    print(f"❌ 스캔 오류: {error}")
    exit(1)

print(f"📱 발견된 네트워크: {len(networks)}개\n")

# 모든 네트워크 출력
all_networks = []
for network in networks:
    ssid = network.ssid() or "(숨겨진)"
    bssid = normalize_mac(network.bssid() or "")
    rssi = network.rssiValue()
    ch = network.wlanChannel().channelNumber() if network.wlanChannel() else 0
    all_networks.append((ssid, bssid, rssi, ch))

# RSSI 순으로 정렬
print("📶 RSSI 순 (상위 30개):")
print("-" * 80)
print(f"{'RSSI':>6} | {'BSSID':17} | {'CH':>3} | {'SSID'}")
print("-" * 80)

for ssid, bssid, rssi, ch in sorted(all_networks, key=lambda x: x[2], reverse=True)[:30]:
    bar = "█" * max(0, (rssi + 100) // 4)
    # Aruba OUI 체크
    marker = "🔸" if bssid.startswith("24:F2:7F") else "  "
    print(f"{marker}{rssi:4d} | {bssid:17} | {ch:3} | {ssid[:35]} {bar}")

# Aruba MAC 확인
print("\n" + "=" * 80)
print("🔍 24:F2:7F (Aruba OUI)로 시작하는 AP:")
print("-" * 80)
aruba_aps = [(s, b, r, c) for s, b, r, c in all_networks if b.startswith("24:F2:7F")]
if aruba_aps:
    for ssid, bssid, rssi, ch in sorted(aruba_aps, key=lambda x: x[2], reverse=True):
        print(f"  {rssi:4d} dBm | {bssid} | ch.{ch:3} | {ssid}")
else:
    print("  (없음)")

# hallym 검색
print("\n🔍 'hallym' 포함 SSID:")
print("-" * 80)
hallym_aps = [(s, b, r, c) for s, b, r, c in all_networks if "hallym" in s.lower()]
if hallym_aps:
    for ssid, bssid, rssi, ch in sorted(hallym_aps, key=lambda x: x[2], reverse=True):
        print(f"  {rssi:4d} dBm | {bssid} | ch.{ch:3} | {ssid}")
else:
    print("  (없음)")
