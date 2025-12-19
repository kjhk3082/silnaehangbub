#!/usr/bin/env python3
"""
WiFi RSSI 기반 스캐너
macOS CoreWLAN 프레임워크를 사용하여 WiFi AP 스캔
"""

import subprocess
from typing import Dict, List, Tuple
from config import ARUBA_APS, AP_POSITIONS, RSSI_MIN

# Aruba AP의 Ethernet MAC 주소 (WiFi BSSID)
ARUBA_WIFI_MACS = {
    "24:F2:7F:C7:F5:6A": "AP-12",  # 7415 근처
    "24:F2:7F:C7:F5:70": "AP-11",  # 7411 앞
    "24:F2:7F:C7:F5:54": "AP-XX",  # 7407-7408 중간
    "24:F2:7F:C7:F5:4E": "AP-09",  # 7405 앞
    "24:F2:7F:C7:F4:B8": "AP-07",  # 복도 끝
    "24:F2:7F:C7:F8:AA": "AP-13",  # 인문2관
    "24:F2:7F:FF:56:B2": "AP-7413",  # 7413 앞 (실측 발견!)
}

def normalize_mac(mac: str) -> str:
    """MAC 주소 정규화 (대문자, 콜론 구분)"""
    mac = mac.upper().replace("-", ":").replace(".", ":")
    mac_clean = mac.replace(":", "")
    if len(mac_clean) == 12:
        return ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))
    return mac


class WiFiScanner:
    """macOS WiFi 스캐너 (CoreWLAN 사용)"""
    
    def __init__(self):
        self.last_rssi: Dict[str, float] = {}
        self.client = None
        self.interface = None
        self._init_corewlan()
        
    def _init_corewlan(self):
        """CoreWLAN 초기화"""
        try:
            from CoreWLAN import CWWiFiClient
            self.client = CWWiFiClient.sharedWiFiClient()
            self.interface = self.client.interface()
            if self.interface:
                print(f"✅ WiFi 인터페이스: {self.interface.interfaceName()}")
            else:
                print("❌ WiFi 인터페이스를 찾을 수 없습니다")
        except ImportError:
            print("❌ CoreWLAN을 불러올 수 없습니다")
            print("   pip install pyobjc-framework-CoreWLAN")
        except Exception as e:
            print(f"❌ CoreWLAN 초기화 오류: {e}")
        
    def scan(self) -> Dict[str, float]:
        """
        WiFi 스캔 실행
        
        Returns:
            {AP이름: RSSI} 딕셔너리
        """
        result = {}
        
        if not self.interface:
            print("❌ WiFi 인터페이스가 없습니다")
            return result
        
        try:
            # WiFi 스캔
            networks, error = self.interface.scanForNetworksWithName_error_(None, None)
            
            if error:
                print(f"❌ 스캔 오류: {error}")
                return result
            
            print("\n📡 WiFi 스캔 결과:")
            print("-" * 80)
            
            found_aps = []
            hallym_aps = []
            aruba_unknown = []
            
            for network in networks:
                ssid = network.ssid() or "(숨겨진 SSID)"
                bssid = normalize_mac(network.bssid() or "")
                rssi = network.rssiValue()
                channel = network.wlanChannel().channelNumber() if network.wlanChannel() else 0
                
                # Aruba AP 확인 (등록된 MAC)
                if bssid in ARUBA_WIFI_MACS:
                    ap_name = ARUBA_WIFI_MACS[bssid]
                    result[ap_name] = rssi
                    found_aps.append((ap_name, ssid, bssid, rssi, channel))
                # Aruba OUI (24:F2:7F)로 시작하는 MAC
                elif bssid.startswith("24:F2:7F"):
                    aruba_unknown.append((ssid, bssid, rssi, channel))
                # hallym SSID
                if "hallym" in ssid.lower():
                    hallym_aps.append((ssid, bssid, rssi, channel))
            
            # 발견된 Aruba AP 출력
            if found_aps:
                print("\n✅ 발견된 등록 Aruba AP:")
                for ap_name, ssid, bssid, rssi, ch in sorted(found_aps, key=lambda x: x[3], reverse=True):
                    bar = "█" * max(0, (rssi + 100) // 3)
                    pos = AP_POSITIONS.get(ap_name, (0, 0))
                    print(f"  📶 {ap_name:6} | {rssi:4d} dBm | {bssid} | {ssid[:15]:15} | 위치:({pos[0]:.0f},{pos[1]:.0f}) | {bar}")
            else:
                print("\n❌ 등록된 Aruba AP를 찾지 못했습니다")
            
            # 미등록 Aruba AP
            if aruba_unknown:
                print("\n🔸 미등록 Aruba AP (24:F2:7F...):")
                for ssid, bssid, rssi, ch in sorted(aruba_unknown, key=lambda x: x[2], reverse=True):
                    bar = "█" * max(0, (rssi + 100) // 3)
                    print(f"  {rssi:4d} dBm | {bssid} | {ssid[:20]:20} | ch.{ch:3} | {bar}")
            
            # hallym AP들
            if hallym_aps:
                print(f"\n📋 'hallym' SSID ({len(hallym_aps)}개):")
                for ssid, bssid, rssi, ch in sorted(hallym_aps, key=lambda x: x[2], reverse=True)[:10]:
                    bar = "█" * max(0, (rssi + 100) // 3)
                    # 등록 여부 표시
                    marker = "✓" if bssid in ARUBA_WIFI_MACS else " "
                    print(f"  {marker} {rssi:4d} dBm | {bssid} | {ssid[:25]:25} | ch.{ch:3} | {bar}")
            
            # 감지되지 않은 AP는 RSSI_MIN으로 설정
            for mac, ap_name in ARUBA_WIFI_MACS.items():
                if ap_name not in result:
                    result[ap_name] = RSSI_MIN
                    
        except Exception as e:
            print(f"❌ WiFi 스캔 오류: {e}")
            import traceback
            traceback.print_exc()
        
        self.last_rssi = result
        return result
    
    def get_rssi_list(self) -> List[Tuple[str, Tuple[float, float], float]]:
        """위치 추정용 RSSI 리스트"""
        result = []
        for ap_name, rssi in self.last_rssi.items():
            if rssi > RSSI_MIN and ap_name in AP_POSITIONS:
                result.append((ap_name, AP_POSITIONS[ap_name], rssi))
        return result


def scan_and_estimate():
    """WiFi 스캔 후 위치 추정"""
    from position_estimator import PositionEstimator
    from config import get_nearest_room, get_corridor
    
    print("=" * 80)
    print("📡 WiFi RSSI 기반 실내 위치 추정")
    print("=" * 80)
    
    # WiFi 스캔
    scanner = WiFiScanner()
    rssi_result = scanner.scan()
    
    # 감지된 AP 수 확인
    detected = [ap for ap, rssi in rssi_result.items() if rssi > RSSI_MIN]
    print(f"\n📊 감지된 AP: {len(detected)}개 / 6개")
    
    if len(detected) < 3:
        print("⚠️ 위치 추정에 최소 3개 AP가 필요합니다")
        print("\n💡 힌트: 등록되지 않은 Aruba AP가 있다면 config.py에 추가하세요")
        return None
    
    # 위치 추정
    print("\n" + "=" * 80)
    print("📍 위치 추정 결과:")
    print("-" * 80)
    
    methods = ["weighted_centroid", "trilateration", "least_squares"]
    results = {}
    
    for method in methods:
        estimator = PositionEstimator(method=method)
        position = estimator.estimate(rssi_result)
        
        if position:
            x, y = position
            room = get_nearest_room(x, y)
            corridor = get_corridor(x, y)
            results[method] = (x, y, room)
            print(f"  {method:20} → ({x:5.1f}m, {y:5.1f}m) | 호실: {room:5} | 복도: {corridor or 'N/A'}")
        else:
            print(f"  {method:20} → 추정 실패")
    
    # 최종 결과
    if "weighted_centroid" in results:
        x, y, room = results["weighted_centroid"]
        print("\n" + "=" * 80)
        print(f"🎯 추정 위치: ({x:.1f}m, {y:.1f}m)")
        print(f"🏠 가장 가까운 호실: {room}")
        print("=" * 80)
        return (x, y, room)
    
    return None


if __name__ == "__main__":
    scan_and_estimate()
