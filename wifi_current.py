#!/usr/bin/env python3
"""
현재 연결된 WiFi 정보 확인 + 연결 후 스캔
"""

from CoreWLAN import CWWiFiClient
import subprocess

def normalize_mac(mac: str) -> str:
    if not mac:
        return ""
    mac = mac.upper().replace("-", ":").replace(".", ":")
    mac_clean = mac.replace(":", "")
    if len(mac_clean) == 12:
        return ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))
    return mac

# 등록된 Aruba AP
ARUBA_WIFI_MACS = {
    "24:F2:7F:C7:F5:6A": "AP-12 (7415 근처)",
    "24:F2:7F:C7:F5:70": "AP-11 (7411 앞)",
    "24:F2:7F:C7:F5:54": "AP-XX (7407-7408)",
    "24:F2:7F:C7:F5:4E": "AP-09 (7405 앞)",
    "24:F2:7F:C7:F4:B8": "AP-07 (복도 끝)",
    "24:F2:7F:C7:F8:AA": "AP-13 (인문2관)",
}

print("=" * 70)
print("📡 현재 WiFi 연결 정보")
print("=" * 70)

client = CWWiFiClient.sharedWiFiClient()
interface = client.interface()

if not interface:
    print("❌ WiFi 인터페이스 없음")
    exit(1)

# 현재 연결 정보
ssid = interface.ssid()
bssid = normalize_mac(interface.bssid() or "")
rssi = interface.rssiValue()
channel = interface.wlanChannel()
ch_num = channel.channelNumber() if channel else 0

print(f"\n인터페이스: {interface.interfaceName()}")
print(f"전원 상태: {'켜짐' if interface.powerOn() else '꺼짐'}")

if ssid:
    print(f"\n✅ 현재 연결된 WiFi:")
    print(f"   SSID: {ssid}")
    print(f"   BSSID: {bssid}")
    print(f"   RSSI: {rssi} dBm")
    print(f"   채널: {ch_num}")
    
    # Aruba AP인지 확인
    if bssid in ARUBA_WIFI_MACS:
        ap_name = ARUBA_WIFI_MACS[bssid]
        print(f"\n   🎯 등록된 Aruba AP: {ap_name}")
    elif bssid.startswith("24:F2:7F"):
        print(f"\n   🔸 미등록 Aruba AP입니다!")
        print(f"      이 MAC 주소를 config.py에 추가하세요")
    
    # 위치 추정 시도
    if bssid.startswith("24:F2:7F"):
        print("\n" + "=" * 70)
        print("📍 현재 연결된 AP 기반 위치 추정")
        print("-" * 70)
        
        from config import AP_POSITIONS, get_nearest_room
        
        if bssid in ARUBA_WIFI_MACS:
            ap_name = ARUBA_WIFI_MACS[bssid].split(" ")[0]  # "AP-12" 부분만
            if ap_name in AP_POSITIONS:
                pos = AP_POSITIONS[ap_name]
                room = get_nearest_room(pos[0], pos[1])
                print(f"   현재 AP 위치: ({pos[0]:.1f}m, {pos[1]:.1f}m)")
                print(f"   가장 가까운 호실: {room}")
else:
    print("\n❌ WiFi에 연결되어 있지 않습니다")
    print("   hallym wifi에 연결해주세요!")

# 대안: networksetup 명령어로 현재 네트워크 정보 확인
print("\n" + "=" * 70)
print("📋 networksetup 명령어로 확인:")
print("-" * 70)
try:
    result = subprocess.run(
        ["networksetup", "-getairportnetwork", "en0"],
        capture_output=True, text=True
    )
    print(f"   {result.stdout.strip()}")
except Exception as e:
    print(f"   오류: {e}")

# arp 테이블에서 MAC 주소 확인
print("\n📋 ARP 테이블에서 Aruba AP 확인:")
print("-" * 70)
try:
    result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
    for line in result.stdout.split("\n"):
        if "24:f2:7f" in line.lower():
            print(f"   {line}")
except:
    pass
