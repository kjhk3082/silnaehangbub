"""
Aruba AP 기반 실내 위치 추정 시스템 설정
6대의 AP BLE MAC 주소 및 위치 정보

좌표계: 7415호실 왼쪽 아래 = 원점 (0, 0)
단위: 미터 (m)
"""

import json
import os

# ============================================================
# 호실 좌표 데이터 로드
# ============================================================
ROOM_DATA_FILE = os.path.join(os.path.dirname(__file__), "room", "rooms_coords_7415_origin.json")

def load_room_data():
    """호실 좌표 데이터 로드"""
    try:
        with open(ROOM_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"호실 데이터 로드 실패: {e}")
        return None

ROOM_DATA = load_room_data()

# 호실별 중심 좌표 딕셔너리
ROOM_CENTROIDS = {}
if ROOM_DATA:
    for room in ROOM_DATA.get("rooms", []):
        ROOM_CENTROIDS[room["room"]] = tuple(room["centroid_m"])

# ============================================================
# Aruba AP 정보 (BLE MAC 주소)
# 좌표: 7415 원점 기준
# ============================================================
# 아래쪽 복도 AP 순서: AP-12 → AP-11 → AP-XX → AP-07
# (7415 근처부터 7401 방향으로)

ARUBA_APS = {
    # ========== 아래쪽 복도 (7415 → 7401 방향) ==========
    "AP-12": {
        "location": "자연과학 4층",
        "ethernet_mac": "24:F2:7F:C7:F5:6A",
        "ble_mac": "3C:A3:08:03:C5:40",
        # 첫 번째 AP - 7415 근처
        "position": (5.0, 3.5),
        "description": "자연과학관 4층 - 7415 근처 (복도 시작)"
    },
    "AP-11": {
        "location": "자연과학 4층",
        "ethernet_mac": "24:F2:7F:C7:F5:70",
        "ble_mac": "3C:A3:08:03:37:29",
        # 두 번째 AP - 7411 앞 천장
        "position": (25.3, 3.5),
        "description": "자연과학관 4층 - 7411 앞 천장"
    },
    "AP-XX": {
        "location": "자연과학 4층",
        "ethernet_mac": "24:F2:7F:C7:F5:54",
        "ble_mac": "3C:A3:08:03:CA:27",
        # 세 번째 AP - 7407-7408 중간
        "position": (38.2, 3.5),
        "description": "자연과학관 4층 - 7407-7408 중간 (번호 미표기)"
    },
    "AP-09": {
        "location": "자연과학 4층",
        "ethernet_mac": "24:F2:7F:C7:F5:4E",
        "ble_mac": "3C:A3:08:03:A2:85",
        # 네 번째 AP - 7405 앞
        "position": (47.3, 3.5),
        "description": "자연과학관 4층 - 7405 앞"
    },
    "AP-07": {
        "location": "자연과학 4층",
        "ethernet_mac": "24:F2:7F:C7:F4:B8",
        "ble_mac": "3C:A3:08:11:93:9E",
        # 다섯 번째 AP - 복도 끝 (7401 근처)
        "position": (58.7, 3.5),
        "description": "자연과학관 4층 - 복도 끝 (7401 근처)"
    },
    
    # ========== 위쪽 복도 (인문2관) ==========
    "AP-13": {
        "location": "인문2 4층",
        "ethernet_mac": "24:F2:7F:C7:F8:AA",
        "ble_mac": "3C:A3:08:08:73:6A",
        # 위쪽 복도 끝 - 7430 근처
        "position": (67.0, 16.5),
        "description": "인문2관 4층 - 7430 근처"
    },
    
    # ========== 실측 발견 AP ==========
    "AP-7413": {
        "location": "자연과학 4층",
        "ethernet_mac": "24:F2:7F:FF:56:B2",  # WiFi BSSID (실측)
        "ble_mac": "unknown",
        # 7413 앞 - 실측으로 발견
        "position": (9.1, 3.1),
        "description": "자연과학관 4층 - 7413 앞 (실측 발견)"
    }
}

# BLE MAC 주소 리스트 (스캔용)
BLE_MAC_LIST = [ap["ble_mac"].upper() for ap in ARUBA_APS.values()]

# AP 이름과 BLE MAC 매핑
BLE_MAC_TO_AP = {ap["ble_mac"].upper(): name for name, ap in ARUBA_APS.items()}
AP_TO_BLE_MAC = {name: ap["ble_mac"].upper() for name, ap in ARUBA_APS.items()}

# AP 위치 좌표
AP_POSITIONS = {name: ap["position"] for name, ap in ARUBA_APS.items()}

# ============================================================
# RSSI → 거리 변환 파라미터
# ============================================================
TX_POWER = -59          # 1m 기준 RSSI (dBm) - 환경에 맞게 조정
PATH_LOSS_EXPONENT = 2.5  # 실내 환경 경로 손실 지수 (2.0~4.0)
RSSI_FILTER_WINDOW = 5   # RSSI 이동평균 필터 윈도우 크기
RSSI_MIN = -100          # 최소 RSSI 임계값

# ============================================================
# 위치 추정 파라미터
# ============================================================
POSITION_UPDATE_INTERVAL = 1.0   # 위치 업데이트 간격 (초)
MIN_AP_FOR_TRILATERATION = 3     # 삼변측량에 필요한 최소 AP 수
MAX_DISTANCE = 30.0              # 최대 인식 거리 (미터)

# ============================================================
# 맵 설정 (7415 원점 기준)
# ============================================================
MAP_WIDTH = 75.0   # 맵 가로 크기 (미터)
MAP_HEIGHT = 22.0  # 맵 세로 크기 (미터)
MAP_SCALE = 10     # 픽셀/미터 비율 (시각화용)

# 맵 경계
MAP_BOUNDS = {
    "min_x": -2,
    "max_x": MAP_WIDTH,
    "min_y": -3,
    "max_y": MAP_HEIGHT
}

# 복도 영역 정의
CORRIDORS = {
    "lower": {  # 아래쪽 복도 (7415 ~ 7401)
        "x_range": (0, 62),
        "y_range": (0, 6.5),
        "rooms": ["7415", "7414", "7413", "7412", "7411", "7410", 
                  "7409", "7408", "7407", "7406", "7405", "7404", "7403", "7401"],
        "aps": ["AP-12", "AP-11", "AP-XX", "AP-09", "AP-07"]  # 순서대로 5개
    },
    "upper": {  # 위쪽 복도 (7416 ~ 7430) - 인문2관
        "x_range": (0, 73),
        "y_range": (13, 21),
        "rooms": ["7416", "7420", "7422", "7423", "7424", "7425", "7429", "7430"],
        "aps": ["AP-13"]  # 1개
    }
}

# ============================================================
# 로그 설정
# ============================================================
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "position_log.json")
TRAJECTORY_FILE = os.path.join(LOG_DIR, "trajectory.json")

# 로그 디렉토리 생성
os.makedirs(LOG_DIR, exist_ok=True)

# ============================================================
# 유틸리티 함수
# ============================================================
def rssi_to_distance(rssi):
    """
    RSSI 값을 거리(미터)로 변환
    Log-distance path loss model 사용
    """
    if rssi >= 0 or rssi < RSSI_MIN:
        return MAX_DISTANCE
    
    distance = 10 ** ((TX_POWER - rssi) / (10 * PATH_LOSS_EXPONENT))
    return min(distance, MAX_DISTANCE)


def get_ap_by_mac(ble_mac):
    """BLE MAC 주소로 AP 정보 가져오기"""
    ble_mac = ble_mac.upper()
    if ble_mac in BLE_MAC_TO_AP:
        ap_name = BLE_MAC_TO_AP[ble_mac]
        return ARUBA_APS[ap_name]
    return None


def get_nearest_room(x, y):
    """
    좌표에서 가장 가까운 호실 찾기
    """
    if not ROOM_CENTROIDS:
        return None
    
    import math
    min_dist = float('inf')
    nearest_room = None
    
    for room_num, centroid in ROOM_CENTROIDS.items():
        dist = math.sqrt((x - centroid[0])**2 + (y - centroid[1])**2)
        if dist < min_dist:
            min_dist = dist
            nearest_room = room_num
    
    return nearest_room


def get_corridor(x, y):
    """
    좌표가 어느 복도에 있는지 확인
    """
    for name, corridor in CORRIDORS.items():
        x_min, x_max = corridor["x_range"]
        y_min, y_max = corridor["y_range"]
        if x_min <= x <= x_max and y_min <= y <= y_max:
            return name
    return None


def print_ap_info():
    """AP 정보 출력"""
    print("\n" + "=" * 70)
    print("📡 Aruba AP 설정 정보 (7415 원점 기준)")
    print("=" * 70)
    
    print("\n🔽 아래쪽 복도 (7415 → 7401) - 5개 AP:")
    for ap_name in ["AP-12", "AP-11", "AP-XX", "AP-09", "AP-07"]:
        info = ARUBA_APS[ap_name]
        print(f"  [{ap_name}] 위치: ({info['position'][0]:.1f}m, {info['position'][1]:.1f}m)")
        print(f"           BLE MAC: {info['ble_mac']}")
        print(f"           {info['description']}")
    
    print("\n🔼 위쪽 복도 (인문2관) - 1개 AP:")
    for ap_name in ["AP-13"]:
        info = ARUBA_APS[ap_name]
        print(f"  [{ap_name}] 위치: ({info['position'][0]:.1f}m, {info['position'][1]:.1f}m)")
        print(f"           BLE MAC: {info['ble_mac']}")
        print(f"           {info['description']}")
    
    print("\n" + "=" * 70)


def print_room_info():
    """주요 호실 정보 출력"""
    print("\n" + "=" * 70)
    print("🏢 주요 호실 좌표 (7415 원점 기준)")
    print("=" * 70)
    
    # 아래쪽 복도
    print("\n📍 아래쪽 복도:")
    lower_rooms = ["7415", "7414", "7413", "7412", "7411", "7410", 
                   "7409", "7408", "7407", "7406", "7405", "7404", "7403", "7401"]
    for room in lower_rooms:
        if room in ROOM_CENTROIDS:
            cx, cy = ROOM_CENTROIDS[room]
            print(f"   {room}: ({cx:.1f}m, {cy:.1f}m)")
    
    # 위쪽 복도
    print("\n📍 위쪽 복도:")
    upper_rooms = ["7416", "7420", "7422", "7423", "7424", "7425", "7429", "7430"]
    for room in upper_rooms:
        if room in ROOM_CENTROIDS:
            cx, cy = ROOM_CENTROIDS[room]
            print(f"   {room}: ({cx:.1f}m, {cy:.1f}m)")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print_ap_info()
    print_room_info()
    
    # 거리 변환 테스트
    print("\n📏 RSSI → 거리 변환 테스트:")
    test_rssi = [-50, -60, -70, -80, -90]
    for rssi in test_rssi:
        dist = rssi_to_distance(rssi)
        print(f"  RSSI {rssi} dBm → {dist:.2f}m")
    
    # 가장 가까운 호실 테스트 (각 AP 위치)
    print("\n🏠 AP 위치 → 가장 가까운 호실:")
    for ap_name in ["AP-12", "AP-11", "AP-XX", "AP-09", "AP-07", "AP-13"]:
        x, y = ARUBA_APS[ap_name]["position"]
        room = get_nearest_room(x, y)
        corridor = get_corridor(x, y)
        print(f"  {ap_name} ({x}, {y}) → 호실 {room}, 복도: {corridor}")
