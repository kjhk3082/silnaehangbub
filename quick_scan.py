#!/usr/bin/env python3
"""
빠른 BLE 스캔 테스트
주변의 모든 BLE 기기를 스캔하고 Aruba AP를 찾습니다.
"""

import asyncio
from bleak import BleakScanner

# Aruba AP BLE MAC 주소 목록
ARUBA_BLE_MACS = {
    "3C:A3:08:03:C5:40": "AP-12 (7415 근처)",
    "3C:A3:08:03:37:29": "AP-11 (7411 앞)",
    "3C:A3:08:03:CA:27": "AP-XX (7407-7408 중간)",
    "3C:A3:08:03:A2:85": "AP-09 (7405 앞)",
    "3C:A3:08:11:93:9E": "AP-07 (복도 끝)",
    "3C:A3:08:08:73:6A": "AP-13 (인문2관)",
}

async def scan_all():
    """모든 BLE 기기 스캔"""
    print("=" * 60)
    print("🔍 BLE 스캔 시작 (5초)...")
    print("=" * 60)
    
    # 콜백으로 RSSI 수집
    devices_dict = {}
    
    def detection_callback(device, advertisement_data):
        devices_dict[device.address.upper()] = {
            "name": device.name or advertisement_data.local_name or "(이름 없음)",
            "rssi": advertisement_data.rssi,
            "device": device
        }
    
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    await asyncio.sleep(5.0)
    await scanner.stop()
    
    print(f"\n📱 발견된 BLE 기기: {len(devices_dict)}개\n")
    
    # Aruba AP 찾기
    found_aps = []
    other_devices = []
    
    for mac, info in devices_dict.items():
        name = info["name"]
        rssi = info["rssi"]
        
        if mac in ARUBA_BLE_MACS:
            found_aps.append((mac, name, rssi, ARUBA_BLE_MACS[mac]))
        else:
            other_devices.append((mac, name, rssi))
    
    # Aruba AP 출력
    if found_aps:
        print("✅ 발견된 Aruba AP:")
        print("-" * 60)
        for mac, name, rssi, ap_info in sorted(found_aps, key=lambda x: x[2], reverse=True):
            print(f"  📡 {ap_info}")
            print(f"     MAC: {mac}")
            print(f"     이름: {name}")
            print(f"     RSSI: {rssi} dBm")
            print()
    else:
        print("❌ Aruba AP를 찾지 못했습니다.")
        print("   (BLE가 활성화되어 있는지 확인하세요)")
    
    # 3C:A3로 시작하는 기기 (Aruba 제조사)
    print("\n📋 3C:A3로 시작하는 기기 (Aruba 제조사):")
    print("-" * 60)
    aruba_like = [(m, n, r) for m, n, r in other_devices if m.startswith("3C:A3")]
    if aruba_like:
        for mac, name, rssi in sorted(aruba_like, key=lambda x: x[2], reverse=True):
            print(f"  {rssi:4d} dBm | {mac} | {name}")
    else:
        print("  (없음)")
    
    # hallym 관련 기기
    print("\n📋 'hallym' 또는 'aruba' 이름 포함 기기:")
    print("-" * 60)
    hallym_devices = [(m, n, r) for m, n, r in other_devices 
                      if "hallym" in n.lower() or "aruba" in n.lower()]
    if hallym_devices:
        for mac, name, rssi in sorted(hallym_devices, key=lambda x: x[2], reverse=True):
            print(f"  {rssi:4d} dBm | {mac} | {name}")
    else:
        print("  (없음 - WiFi SSID는 BLE에서 안 보입니다)")
    
    # 상위 15개 기기
    print("\n📋 RSSI 상위 15개 기기:")
    print("-" * 60)
    for mac, name, rssi in sorted(other_devices, key=lambda x: x[2], reverse=True)[:15]:
        print(f"  {rssi:4d} dBm | {mac} | {name[:35]}")
    
    return found_aps

if __name__ == "__main__":
    found = asyncio.run(scan_all())
    
    if found:
        print("\n" + "=" * 60)
        print("📍 위치 추정 가능!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("💡 AP의 BLE 기능이 켜져 있는지 확인하세요")
        print("   (Aruba AP는 BLE 비콘 기능을 별도로 활성화해야 합니다)")
        print("=" * 60)
