#!/usr/bin/env python3
"""
WiFi 스캔 테스트 - 주변 AP 목록 가져오기 시도
"""

try:
    from CoreWLAN import CWWiFiClient, CWNetwork
    
    client = CWWiFiClient.sharedWiFiClient()
    interface = client.interface()
    
    print("=" * 60)
    print("📡 WiFi 스캔 테스트")
    print("=" * 60)
    print(f"인터페이스: {interface.interfaceName()}")
    print(f"현재 연결: {interface.ssid()}")
    print(f"현재 BSSID: {interface.bssid()}")
    print(f"현재 RSSI: {interface.rssiValue()} dBm")
    print()
    
    # 방법 1: scanForNetworksWithSSID (특정 SSID로 스캔)
    print("🔍 방법 1: scanForNetworksWithSSID")
    try:
        networks, error = interface.scanForNetworksWithSSID_error_(None, None)
        if networks:
            print(f"  발견된 네트워크: {len(networks)}개")
            for i, network in enumerate(networks):
                if i >= 10:
                    print(f"  ... 외 {len(networks) - 10}개")
                    break
                ssid = network.ssid() or "(숨김)"
                bssid = network.bssid() or "(숨김)"
                rssi = network.rssiValue()
                print(f"  [{i+1}] SSID: {ssid}, BSSID: {bssid}, RSSI: {rssi}")
        else:
            print(f"  실패: {error}")
    except Exception as e:
        print(f"  에러: {e}")
    
    print()
    
    # 방법 2: scanForNetworksWithName (이름으로 스캔)
    print("🔍 방법 2: scanForNetworksWithName ('Hallym')")
    try:
        networks, error = interface.scanForNetworksWithName_error_("Hallym", None)
        if networks:
            print(f"  발견된 네트워크: {len(networks)}개")
            for network in networks:
                ssid = network.ssid() or "(숨김)"
                bssid = network.bssid() or "(숨김)"
                rssi = network.rssiValue()
                print(f"  SSID: {ssid}, BSSID: {bssid}, RSSI: {rssi}")
        else:
            print(f"  실패: {error}")
    except Exception as e:
        print(f"  에러: {e}")
    
    print()
    
    # 방법 3: cachedScanResults
    print("🔍 방법 3: cachedScanResults")
    try:
        cached = interface.cachedScanResults()
        if cached:
            print(f"  캐시된 네트워크: {len(cached)}개")
            for i, network in enumerate(cached):
                if i >= 10:
                    print(f"  ... 외 {len(cached) - 10}개")
                    break
                ssid = network.ssid() or "(숨김)"
                bssid = network.bssid() or "(숨김)"
                rssi = network.rssiValue()
                print(f"  [{i+1}] SSID: {ssid}, BSSID: {bssid}, RSSI: {rssi}")
        else:
            print("  캐시 없음")
    except Exception as e:
        print(f"  에러: {e}")

except ImportError:
    print("CoreWLAN 없음")
except Exception as e:
    print(f"에러: {e}")
