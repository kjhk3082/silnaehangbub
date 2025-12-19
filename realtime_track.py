#!/usr/bin/env python3
"""
실시간 위치 추적 및 궤적 기록
7413 = 원점 (0, 0)
복도를 따라 이동하면서 위치 기록
"""

import time
import json
import os
from datetime import datetime

try:
    from CoreWLAN import CWWiFiClient
    USE_WIFI = True
except:
    USE_WIFI = False
    print("⚠️ CoreWLAN 없음 - 수동 입력 모드")

# ============================================================
# 설정: 7413 = 원점 (0, 0)
# ============================================================
ORIGIN_ROOM = "7413"
ORIGIN_X = 9.1  # 기존 좌표계에서 7413의 X

# 캘리브레이션 데이터 (7413 원점 기준으로 변환)
# (호실, RSSI, 7413 기준 거리)
CALIBRATION = [
    ("7413", -38,  0.0),    # 원점
    ("7411", -56,  16.2),   # 25.3 - 9.1
    ("7408", -58,  27.2),   # 36.3 - 9.1
    ("7405", -63,  38.2),   # 47.3 - 9.1
    ("7401", -68,  51.7),   # 60.8 - 9.1
]

# 호실 위치 (7413 기준)
ROOM_POSITIONS = {
    "7413": 0.0,
    "7412": 12.2,
    "7411": 16.2,
    "7410": 19.8,
    "7409": 23.5,
    "7408": 27.2,
    "7407": 30.9,
    "7406": 34.6,
    "7405": 38.2,
    "7404": 41.9,
    "7403": 45.5,
    "7401": 49.6,
}

def normalize_mac(mac):
    if not mac:
        return ""
    mac = mac.upper().replace("-", ":").replace(".", ":")
    mac_clean = mac.replace(":", "")
    if len(mac_clean) == 12:
        return ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))
    return mac

def rssi_to_position(rssi):
    """RSSI → 7413 기준 위치 (미터)"""
    rssi_list = [c[1] for c in CALIBRATION]
    pos_list = [c[2] for c in CALIBRATION]
    
    if rssi >= rssi_list[0]:
        return pos_list[0]
    elif rssi <= rssi_list[-1]:
        # 외삽
        return pos_list[-1] + (rssi_list[-1] - rssi) * 1.0
    else:
        # 선형 보간
        for i in range(len(rssi_list) - 1):
            if rssi_list[i] >= rssi >= rssi_list[i+1]:
                ratio = (rssi_list[i] - rssi) / (rssi_list[i] - rssi_list[i+1])
                return pos_list[i] + ratio * (pos_list[i+1] - pos_list[i])
    return 0

def get_nearest_room(pos):
    """위치에서 가장 가까운 호실"""
    min_dist = float('inf')
    nearest = "7413"
    for room, room_pos in ROOM_POSITIONS.items():
        dist = abs(pos - room_pos)
        if dist < min_dist:
            min_dist = dist
            nearest = room
    return nearest, min_dist

def draw_track(trajectory, current_pos=None):
    """ASCII 아트로 궤적 표시"""
    width = 60
    max_pos = 55  # 최대 위치 (미터)
    
    # 복도 그리기
    corridor = ['-'] * width
    
    # 호실 위치 표시
    for room, pos in ROOM_POSITIONS.items():
        idx = int(pos / max_pos * (width - 1))
        if 0 <= idx < width:
            corridor[idx] = '|'
    
    # 궤적 표시
    track_line = [' '] * width
    for point in trajectory:
        idx = int(point['position'] / max_pos * (width - 1))
        if 0 <= idx < width:
            track_line[idx] = '·'
    
    # 현재 위치 표시
    if current_pos is not None:
        idx = int(current_pos / max_pos * (width - 1))
        if 0 <= idx < width:
            track_line[idx] = '●'
    
    # 출력
    print("\n" + "7413" + " " * 23 + "7408" + " " * 11 + "7405" + " " * 8 + "7401")
    print(" " + "".join(corridor))
    print(" " + "".join(track_line))
    print(f" 0m{' ' * 24}~27m{' ' * 10}~38m{' ' * 8}~52m")

def main():
    print("=" * 70)
    print("🚶 실시간 위치 추적 (7413 = 원점)")
    print("=" * 70)
    print(f"\n📍 원점: {ORIGIN_ROOM} (0, 0)")
    print("📏 복도 방향: 7413 → 7411 → 7408 → 7405 → 7401")
    print("\n" + "-" * 70)
    
    # 궤적 데이터
    trajectory = []
    start_time = time.time()
    
    # WiFi 초기화
    if USE_WIFI:
        client = CWWiFiClient.sharedWiFiClient()
        interface = client.interface()
        if not interface:
            print("❌ WiFi 인터페이스 없음")
            return
        print(f"✅ WiFi: {interface.interfaceName()}")
    
    print("\n🎬 추적 시작! (Ctrl+C로 종료)")
    print("-" * 70)
    
    last_pos = 0
    last_room = "7413"
    
    try:
        while True:
            elapsed = time.time() - start_time
            
            if USE_WIFI:
                # WiFi RSSI 읽기
                rssi = interface.rssiValue()
                bssid = normalize_mac(interface.bssid() or "")
            else:
                # 수동 입력 모드
                try:
                    rssi = int(input(f"[{elapsed:.0f}s] RSSI 입력: "))
                except:
                    continue
            
            # 위치 계산
            pos = rssi_to_position(rssi)
            room, dist = get_nearest_room(pos)
            
            # 이동 방향
            if pos > last_pos + 0.5:
                direction = "→ 전진"
            elif pos < last_pos - 0.5:
                direction = "← 후진"
            else:
                direction = "· 정지"
            
            # 호실 변경 감지
            room_changed = room != last_room
            
            # 기록
            point = {
                "time": elapsed,
                "rssi": rssi,
                "position": pos,
                "room": room,
                "direction": direction
            }
            trajectory.append(point)
            
            # 출력
            pos_bar = "█" * int(pos / 52 * 30)
            room_marker = f"🆕 {room}" if room_changed else f"   {room}"
            
            print(f"\r[{elapsed:5.1f}s] RSSI:{rssi:4d}dBm | 위치:{pos:5.1f}m | {room_marker} | {direction} |{pos_bar}", end="", flush=True)
            
            if room_changed:
                print()  # 호실 바뀌면 줄바꿈
            
            last_pos = pos
            last_room = room
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        pass
    
    # 결과 저장
    print("\n\n" + "=" * 70)
    print("📊 추적 결과")
    print("=" * 70)
    
    if trajectory:
        # 통계
        positions = [p['position'] for p in trajectory]
        min_pos = min(positions)
        max_pos = max(positions)
        
        print(f"\n총 시간: {trajectory[-1]['time']:.1f}초")
        print(f"기록 포인트: {len(trajectory)}개")
        print(f"이동 범위: {min_pos:.1f}m ~ {max_pos:.1f}m")
        print(f"총 이동 거리: {max_pos - min_pos:.1f}m")
        
        # 방문한 호실
        rooms_visited = list(dict.fromkeys([p['room'] for p in trajectory]))
        print(f"방문 호실: {' → '.join(rooms_visited)}")
        
        # 궤적 시각화
        draw_track(trajectory, positions[-1])
        
        # JSON 저장
        output = {
            "origin": ORIGIN_ROOM,
            "start_time": datetime.now().isoformat(),
            "duration_sec": trajectory[-1]['time'],
            "trajectory": trajectory,
            "stats": {
                "min_position": min_pos,
                "max_position": max_pos,
                "rooms_visited": rooms_visited
            }
        }
        
        filename = f"logs/track_{datetime.now().strftime('%H%M%S')}.json"
        os.makedirs("logs", exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n💾 저장됨: {filename}")
        
        # matplotlib 시각화
        try:
            import matplotlib.pyplot as plt
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6))
            
            times = [p['time'] for p in trajectory]
            positions = [p['position'] for p in trajectory]
            rssis = [p['rssi'] for p in trajectory]
            
            # 위치 그래프
            ax1.plot(times, positions, 'b-', linewidth=2, label='위치')
            ax1.scatter(times, positions, c='blue', s=10)
            ax1.set_ylabel('위치 (m from 7413)')
            ax1.set_title('🚶 실시간 위치 추적 궤적')
            ax1.grid(True, alpha=0.3)
            
            # 호실 위치 표시
            for room, pos in ROOM_POSITIONS.items():
                ax1.axhline(y=pos, color='gray', linestyle='--', alpha=0.3)
                ax1.text(times[-1], pos, f' {room}', va='center', fontsize=8)
            
            ax1.legend()
            
            # RSSI 그래프
            ax2.plot(times, rssis, 'r-', linewidth=2, label='RSSI')
            ax2.scatter(times, rssis, c='red', s=10)
            ax2.set_xlabel('시간 (초)')
            ax2.set_ylabel('RSSI (dBm)')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
            plt.tight_layout()
            
            img_filename = f"logs/track_{datetime.now().strftime('%H%M%S')}.png"
            plt.savefig(img_filename, dpi=150)
            print(f"📈 그래프 저장됨: {img_filename}")
            
            plt.show()
            
        except ImportError:
            print("(matplotlib 없음 - 그래프 생략)")

if __name__ == "__main__":
    main()
