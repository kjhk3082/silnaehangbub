#!/usr/bin/env python3
"""
단일 AP 기반 위치 추정
복도가 직선이라는 가정하에 RSSI → 거리 → 위치 추정
"""

from config import ARUBA_APS, get_nearest_room, rssi_to_distance

# AP-7413 정보 (7413 앞에 위치)
AP_POSITION = (9.1, 3.1)  # 7413 앞
AP_NAME = "AP-7413"

# 복도 방향 (7413 → 7401, X축 양의 방향)
CORRIDOR_DIRECTION = 1  # +X 방향으로 복도가 뻗어있음
CORRIDOR_Y = 3.1  # 복도 Y 좌표 (고정)

# 실측 데이터로 RSSI-거리 캘리브레이션
CALIBRATION_DATA = [
    # (호실, RSSI, 실제 X좌표)
    ("7413", -38, 9.1),   # AP 위치
    ("7411", -56, 25.3),  # 7411 앞
    ("7408", -58, 36.3),  # 7408 앞
    ("7405", -63, 47.3),  # 7405 앞
    ("7429", -68, 60.8),  # 7429 (위쪽 복도지만 참고용)
]

def estimate_position_single_ap(rssi, ap_x=AP_POSITION[0]):
    """
    단일 AP RSSI로 위치 추정 (복도 직선 가정)
    
    Args:
        rssi: 현재 RSSI 값 (dBm)
        ap_x: AP의 X 좌표
    
    Returns:
        (x, y, nearest_room, confidence)
    """
    # 방법 1: Log-distance model
    distance = rssi_to_distance(rssi)
    
    # 방법 2: 실측 데이터 기반 선형 보간
    # RSSI → X 좌표 직접 매핑
    rssi_values = [d[1] for d in CALIBRATION_DATA]
    x_values = [d[2] for d in CALIBRATION_DATA]
    
    # 선형 보간
    if rssi >= rssi_values[0]:
        # AP보다 가까움
        estimated_x = x_values[0]
    elif rssi <= rssi_values[-1]:
        # 가장 먼 지점보다 멀리
        estimated_x = x_values[-1] + (rssi_values[-1] - rssi) * 0.5
    else:
        # 보간
        for i in range(len(rssi_values) - 1):
            if rssi_values[i] >= rssi >= rssi_values[i+1]:
                # 선형 보간
                ratio = (rssi_values[i] - rssi) / (rssi_values[i] - rssi_values[i+1])
                estimated_x = x_values[i] + ratio * (x_values[i+1] - x_values[i])
                break
    
    # Y는 복도 고정값
    estimated_y = CORRIDOR_Y
    
    # 가장 가까운 호실
    nearest_room = get_nearest_room(estimated_x, estimated_y)
    
    # 신뢰도 계산 (RSSI가 강할수록 높음)
    if rssi > -50:
        confidence = "높음 (AP 근처)"
    elif rssi > -60:
        confidence = "중간"
    elif rssi > -70:
        confidence = "낮음"
    else:
        confidence = "매우 낮음"
    
    return estimated_x, estimated_y, nearest_room, confidence, distance


def print_estimation(rssi, location_hint=""):
    """위치 추정 결과 출력"""
    x, y, room, conf, dist = estimate_position_single_ap(rssi)
    
    print(f"\n{'='*60}")
    print(f"📍 단일 AP 위치 추정 {f'({location_hint})' if location_hint else ''}")
    print(f"{'='*60}")
    print(f"   입력 RSSI: {rssi} dBm")
    print(f"   모델 거리: {dist:.1f}m")
    print(f"   추정 위치: ({x:.1f}m, {y:.1f}m)")
    print(f"   가장 가까운 호실: {room}")
    print(f"   신뢰도: {conf}")
    
    return x, y, room


if __name__ == "__main__":
    print("=" * 60)
    print("📡 단일 AP(AP-7413) 기반 위치 추정")
    print("=" * 60)
    print(f"\nAP 위치: {AP_POSITION}")
    print(f"복도 Y 좌표: {CORRIDOR_Y}m")
    
    # 캘리브레이션 데이터 확인
    print("\n📊 캘리브레이션 데이터:")
    print("-" * 60)
    for room, rssi, x in CALIBRATION_DATA:
        dist = rssi_to_distance(rssi)
        print(f"   {room}: RSSI {rssi:3d} dBm → X={x:.1f}m (모델거리: {dist:.1f}m)")
    
    # 실측 데이터로 테스트
    print("\n" + "=" * 60)
    print("🧪 실측 데이터 검증")
    print("=" * 60)
    
    test_data = [
        (-38, "7413 앞 (실측)"),
        (-56, "7411 앞 (실측)"),
        (-58, "7408 앞 (실측)"),
        (-63, "7405 앞 (실측)"),
        (-68, "7429 근처 (실측)"),
    ]
    
    for rssi, hint in test_data:
        print_estimation(rssi, hint)
    
    # 새 RSSI 입력
    print("\n" + "=" * 60)
    print("🔢 새 RSSI로 테스트 (종료: q)")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\nRSSI 입력 (예: -55): ").strip()
            if user_input.lower() == 'q':
                break
            rssi = int(user_input)
            print_estimation(rssi)
        except ValueError:
            print("숫자를 입력하세요")
        except KeyboardInterrupt:
            break
    
    print("\n👋 종료")
