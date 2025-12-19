#!/usr/bin/env python3
"""
현재 WiFi 연결 기반 위치 추정
"""

from config import ARUBA_APS, AP_POSITIONS, get_nearest_room, rssi_to_distance

# 현재 연결된 AP 정보 (실측값)
CURRENT_BSSID = "24:F2:7F:FF:56:B2"
CURRENT_RSSI = -38  # dBm
CURRENT_AP = "AP-7413"

print("=" * 60)
print("📍 현재 WiFi 기반 위치 추정")
print("=" * 60)

print(f"\n📶 현재 연결:")
print(f"   BSSID: {CURRENT_BSSID}")
print(f"   RSSI: {CURRENT_RSSI} dBm (매우 강함!)")
print(f"   AP: {CURRENT_AP}")

# AP 위치 확인
if CURRENT_AP in AP_POSITIONS:
    ap_pos = AP_POSITIONS[CURRENT_AP]
    print(f"\n📡 AP 위치: ({ap_pos[0]:.1f}m, {ap_pos[1]:.1f}m)")
    
    # RSSI로 거리 추정
    distance = rssi_to_distance(CURRENT_RSSI)
    print(f"📏 추정 거리: {distance:.1f}m")
    
    # 가장 가까운 호실
    room = get_nearest_room(ap_pos[0], ap_pos[1])
    print(f"🏠 가장 가까운 호실: {room}")
    
    print("\n" + "=" * 60)
    print("🎯 결론:")
    print("=" * 60)
    print(f"\n   현재 위치: 약 ({ap_pos[0]:.1f}m, {ap_pos[1]:.1f}m)")
    print(f"   호실: {room} 앞")
    print(f"   신뢰도: RSSI {CURRENT_RSSI}dBm → 거리 약 {distance:.1f}m")
    
    if CURRENT_RSSI > -50:
        print("\n   ✅ 매우 강한 신호! AP 바로 근처에 있습니다.")
    elif CURRENT_RSSI > -60:
        print("\n   ✅ 강한 신호. AP에서 3-5m 이내입니다.")
    elif CURRENT_RSSI > -70:
        print("\n   ⚠️ 보통 신호. AP에서 5-10m 정도입니다.")
    else:
        print("\n   ⚠️ 약한 신호. AP에서 10m 이상 떨어져 있습니다.")

else:
    print(f"\n❌ {CURRENT_AP}가 등록되지 않았습니다")
    print("   config.py에 AP를 추가하세요")

# 다른 AP들과의 비교
print("\n" + "=" * 60)
print("📊 등록된 모든 AP 위치:")
print("-" * 60)
for ap_name, ap_info in ARUBA_APS.items():
    pos = ap_info["position"]
    desc = ap_info["description"]
    marker = "👉" if ap_name == CURRENT_AP else "  "
    print(f"{marker} {ap_name:8} | ({pos[0]:5.1f}m, {pos[1]:5.1f}m) | {desc}")
