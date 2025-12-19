"""
Aruba AP BLE 스캐너 모듈
BLE 신호를 스캔하여 RSSI 값을 수집
"""

import asyncio
import time
from collections import deque
from typing import Dict, List, Optional
from bleak import BleakScanner
from config import (
    BLE_MAC_LIST, BLE_MAC_TO_AP, ARUBA_APS,
    RSSI_FILTER_WINDOW, RSSI_MIN
)


class ArubaBLEScanner:
    """Aruba AP BLE 신호 스캐너"""
    
    def __init__(self, filter_window: int = RSSI_FILTER_WINDOW):
        """
        Args:
            filter_window: RSSI 이동평균 필터 윈도우 크기
        """
        self.filter_window = filter_window
        
        # 각 AP별 RSSI 히스토리 (이동평균 계산용)
        self.rssi_history: Dict[str, deque] = {}
        for ap_name in ARUBA_APS.keys():
            self.rssi_history[ap_name] = deque(maxlen=filter_window)
        
        # 마지막 스캔 결과
        self.last_rssi: Dict[str, float] = {}
        self.last_scan_time: float = 0
        
        # 스캔 상태
        self.is_scanning = False
        
    async def scan_once(self, duration: float = 2.0) -> Dict[str, float]:
        """
        BLE 신호 한 번 스캔
        
        Args:
            duration: 스캔 시간 (초)
            
        Returns:
            AP별 RSSI 딕셔너리 {AP이름: RSSI값}
        """
        self.is_scanning = True
        result = {}
        
        try:
            # BLE 디바이스 스캔
            devices = await BleakScanner.discover(timeout=duration)
            
            for device in devices:
                # MAC 주소 확인 (대문자로 정규화)
                device_mac = device.address.upper()
                
                # Aruba AP의 BLE MAC인지 확인
                if device_mac in BLE_MAC_LIST:
                    ap_name = BLE_MAC_TO_AP[device_mac]
                    rssi = device.rssi
                    
                    # RSSI 히스토리에 추가
                    self.rssi_history[ap_name].append(rssi)
                    
                    # 이동평균 계산
                    filtered_rssi = sum(self.rssi_history[ap_name]) / len(self.rssi_history[ap_name])
                    result[ap_name] = filtered_rssi
                    
                    print(f"  📡 {ap_name}: {rssi} dBm (필터링: {filtered_rssi:.1f} dBm)")
            
            # 스캔되지 않은 AP는 RSSI_MIN으로 설정
            for ap_name in ARUBA_APS.keys():
                if ap_name not in result:
                    result[ap_name] = RSSI_MIN
                    
        except Exception as e:
            print(f"❌ 스캔 오류: {e}")
            # 에러 시 모든 AP를 RSSI_MIN으로 설정
            for ap_name in ARUBA_APS.keys():
                result[ap_name] = RSSI_MIN
        
        finally:
            self.is_scanning = False
            self.last_rssi = result.copy()
            self.last_scan_time = time.time()
        
        return result
    
    def scan_sync(self, duration: float = 2.0) -> Dict[str, float]:
        """
        동기 방식 스캔 (메인 스레드에서 사용)
        
        Args:
            duration: 스캔 시간 (초)
            
        Returns:
            AP별 RSSI 딕셔너리
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.scan_once(duration))
        finally:
            loop.close()
    
    def get_last_rssi(self) -> Dict[str, float]:
        """마지막 스캔 결과 반환"""
        return self.last_rssi.copy()
    
    def get_rssi_list(self) -> List[tuple]:
        """
        RSSI 리스트 반환 (위치 추정용)
        
        Returns:
            [(AP이름, 위치, RSSI), ...] 형태의 리스트
        """
        result = []
        for ap_name, rssi in self.last_rssi.items():
            if rssi > RSSI_MIN:
                position = ARUBA_APS[ap_name]["position"]
                result.append((ap_name, position, rssi))
        return result
    
    def clear_history(self):
        """RSSI 히스토리 초기화"""
        for ap_name in self.rssi_history:
            self.rssi_history[ap_name].clear()
        self.last_rssi = {}


class SimulatedScanner:
    """
    시뮬레이션 스캐너 (테스트/데모용)
    실제 BLE 스캔 없이 가상의 RSSI 값 생성
    """
    
    def __init__(self):
        self.current_position = (35.0, 5.0)  # 시작 위치
        self.last_rssi = {}
        
    def set_position(self, x: float, y: float):
        """현재 위치 설정 (시뮬레이션용)"""
        self.current_position = (x, y)
        
    def scan_sync(self, duration: float = 1.0) -> Dict[str, float]:
        """
        가상 RSSI 값 생성 (거리 기반)
        """
        import math
        import random
        
        result = {}
        x, y = self.current_position
        
        for ap_name, ap_info in ARUBA_APS.items():
            ap_x, ap_y = ap_info["position"]
            
            # 거리 계산
            distance = math.sqrt((x - ap_x)**2 + (y - ap_y)**2)
            
            # Log-distance path loss model로 RSSI 계산
            if distance < 0.5:
                distance = 0.5  # 최소 거리
            
            tx_power = -59
            path_loss = 2.5
            rssi = tx_power - 10 * path_loss * math.log10(distance)
            
            # 노이즈 추가
            rssi += random.gauss(0, 3)
            
            # 범위 제한
            rssi = max(min(rssi, -30), RSSI_MIN)
            
            result[ap_name] = rssi
        
        self.last_rssi = result
        return result
    
    def get_rssi_list(self) -> List[tuple]:
        """RSSI 리스트 반환"""
        result = []
        for ap_name, rssi in self.last_rssi.items():
            if rssi > RSSI_MIN:
                position = ARUBA_APS[ap_name]["position"]
                result.append((ap_name, position, rssi))
        return result


if __name__ == "__main__":
    # 실제 스캐너 테스트
    print("=" * 60)
    print("🔍 Aruba AP BLE 스캐너 테스트")
    print("=" * 60)
    
    # 시뮬레이션 모드로 테스트
    print("\n📌 시뮬레이션 모드 테스트:")
    sim_scanner = SimulatedScanner()
    
    # 위치 변경하며 테스트
    test_positions = [(10, 5), (30, 5), (50, 5), (70, 5)]
    for pos in test_positions:
        sim_scanner.set_position(*pos)
        rssi_result = sim_scanner.scan_sync()
        print(f"\n위치 ({pos[0]}m, {pos[1]}m)에서의 RSSI:")
        for ap, rssi in sorted(rssi_result.items(), key=lambda x: x[1], reverse=True):
            print(f"  {ap}: {rssi:.1f} dBm")
    
    # 실제 스캐너 테스트 (옵션)
    print("\n" + "=" * 60)
    print("📌 실제 BLE 스캔 테스트 (5초):")
    print("=" * 60)
    
    try:
        scanner = ArubaBLEScanner()
        for i in range(3):
            print(f"\n[스캔 {i+1}/3]")
            rssi_result = scanner.scan_sync(duration=2.0)
            
            detected = [ap for ap, rssi in rssi_result.items() if rssi > RSSI_MIN]
            print(f"  감지된 AP: {len(detected)}개")
            
            time.sleep(1)
    except Exception as e:
        print(f"  실제 스캔 불가: {e}")
        print("  (BLE 권한 또는 하드웨어 문제일 수 있음)")
