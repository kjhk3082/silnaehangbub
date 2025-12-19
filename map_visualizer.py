"""
맵 시각화 모듈
실시간 위치 추적 및 궤적 표시
7415 원점 기준 좌표계 사용
"""

import json
import time
import os
from datetime import datetime
from typing import List, Tuple, Optional, Dict
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import PatchCollection
import numpy as np
from config import (
    ARUBA_APS, AP_POSITIONS, MAP_BOUNDS, MAP_SCALE, 
    LOG_FILE, TRAJECTORY_FILE, ROOM_DATA, CORRIDORS
)


class MapVisualizer:
    """
    실내 맵 시각화 클래스
    - 호실 폴리곤 표시
    - AP 위치 표시
    - 현재 위치 표시
    - 이동 궤적 표시
    """
    
    def __init__(self, figsize: Tuple[int, int] = (16, 8)):
        """
        Args:
            figsize: 그림 크기 (인치)
        """
        self.figsize = figsize
        self.fig = None
        self.ax = None
        
        # 궤적 데이터
        self.trajectory: List[Tuple[float, float, float]] = []  # (x, y, timestamp)
        
        # 현재 위치
        self.current_position: Optional[Tuple[float, float]] = None
        
        # 그래픽 요소
        self.position_marker = None
        self.trajectory_line = None
        
    def setup_map(self, show_rooms: bool = True):
        """맵 초기 설정"""
        self.fig, self.ax = plt.subplots(figsize=self.figsize)
        
        # 맵 경계 설정
        self.ax.set_xlim(MAP_BOUNDS["min_x"], MAP_BOUNDS["max_x"])
        self.ax.set_ylim(MAP_BOUNDS["min_y"], MAP_BOUNDS["max_y"])
        
        # 배경 그리기
        if show_rooms and ROOM_DATA:
            self._draw_rooms()
        else:
            self._draw_corridors()
        
        # AP 위치 표시
        self._draw_aps()
        
        # 원점 표시
        self._draw_origin()
        
        # 그리드 설정
        self.ax.grid(True, alpha=0.3, linestyle='--')
        self.ax.set_xlabel('X (미터) - 7415 원점 기준', fontsize=12)
        self.ax.set_ylabel('Y (미터) - 7415 원점 기준', fontsize=12)
        self.ax.set_title('🗺️ Aruba AP 기반 실내 위치 추적 (7415 = 원점)', fontsize=14, fontweight='bold')
        
        # 범례
        self._add_legend()
        
        self.ax.set_aspect('equal')
        plt.tight_layout()
    
    def _draw_rooms(self):
        """호실 폴리곤 그리기"""
        if not ROOM_DATA or "rooms" not in ROOM_DATA:
            return
        
        # 색상 맵
        colors = plt.cm.tab20.colors
        
        for i, room in enumerate(ROOM_DATA["rooms"]):
            room_num = room["room"]
            polygon = room.get("polygon_m", [])
            centroid = room.get("centroid_m", [0, 0])
            
            if not polygon or len(polygon) < 3:
                continue
            
            # 폴리곤 좌표
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            
            # 색상 선택
            color = colors[i % len(colors)]
            
            # 폴리곤 그리기
            poly = patches.Polygon(
                list(zip(xs, ys)),
                closed=True,
                fill=True,
                facecolor=(*color[:3], 0.3),
                edgecolor=(*color[:3], 0.8),
                linewidth=1.5
            )
            self.ax.add_patch(poly)
            
            # 호실 번호 표시 (중심점에)
            cx, cy = centroid
            # 7400번대 호실만 라벨 표시 (너무 많으면 복잡해짐)
            if room_num.startswith("74"):
                self.ax.text(
                    cx, cy, room_num,
                    ha='center', va='center',
                    fontsize=8, fontweight='bold',
                    color='black', alpha=0.8
                )
    
    def _draw_corridors(self):
        """복도 영역 그리기 (호실 데이터 없을 때)"""
        for name, corridor in CORRIDORS.items():
            x_min, x_max = corridor["x_range"]
            y_min, y_max = corridor["y_range"]
            
            rect = patches.Rectangle(
                (x_min, y_min), x_max - x_min, y_max - y_min,
                linewidth=2, edgecolor='gray', 
                facecolor='lightgray', alpha=0.3
            )
            self.ax.add_patch(rect)
            
            # 복도 라벨
            cx = (x_min + x_max) / 2
            cy = (y_min + y_max) / 2
            label = "아래쪽 복도" if name == "lower" else "위쪽 복도"
            self.ax.text(cx, cy, label, ha='center', va='center',
                        fontsize=10, color='gray', alpha=0.7)
        
    def _draw_aps(self):
        """AP 위치 표시"""
        for ap_name, ap_info in ARUBA_APS.items():
            x, y = ap_info["position"]
            
            # AP 마커 (삼각형)
            self.ax.scatter(x, y, marker='^', s=200, c='red', 
                          edgecolors='darkred', linewidths=2, zorder=5)
            
            # AP 이름 표시
            self.ax.annotate(
                ap_name,
                (x, y),
                textcoords="offset points",
                xytext=(0, 12),
                ha='center',
                fontsize=9,
                fontweight='bold',
                color='darkred'
            )
            
            # 범위 원 (반투명)
            circle = patches.Circle(
                (x, y), radius=8,
                fill=False, linestyle='--', 
                edgecolor='red', alpha=0.2
            )
            self.ax.add_patch(circle)
    
    def _draw_origin(self):
        """원점 (7415 왼쪽 아래) 표시"""
        self.ax.scatter(0, 0, marker='o', s=100, c='blue',
                       edgecolors='darkblue', linewidths=2, zorder=6)
        self.ax.annotate(
            "(0,0) = 7415 LL",
            (0, 0),
            textcoords="offset points",
            xytext=(10, -15),
            ha='left',
            fontsize=8,
            color='blue'
        )
    
    def _add_legend(self):
        """범례 추가"""
        legend_elements = [
            plt.scatter([], [], marker='^', s=100, c='red', label='AP 위치'),
            plt.scatter([], [], marker='o', s=150, c='lime', label='현재 위치'),
            plt.Line2D([0], [0], color='blue', linewidth=2, alpha=0.7, label='이동 궤적'),
            plt.scatter([], [], marker='s', s=80, c='green', label='시작점')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right')
    
    def update_position(self, x: float, y: float, timestamp: Optional[float] = None):
        """
        현재 위치 업데이트
        
        Args:
            x, y: 새 위치 좌표
            timestamp: 시간 (None이면 현재 시간)
        """
        if timestamp is None:
            timestamp = time.time()
            
        self.current_position = (x, y)
        self.trajectory.append((x, y, timestamp))
        
        # 이전 마커 제거
        if self.position_marker:
            self.position_marker.remove()
        
        # 새 마커 그리기
        self.position_marker = self.ax.scatter(
            x, y, marker='o', s=250, c='lime',
            edgecolors='darkgreen', linewidths=3, zorder=10
        )
        
        # 궤적 업데이트
        self._update_trajectory()
        
    def _update_trajectory(self):
        """궤적 라인 업데이트"""
        if len(self.trajectory) < 2:
            return
            
        # 이전 궤적 제거
        if self.trajectory_line:
            self.trajectory_line.remove()
        
        # 새 궤적 그리기
        xs = [p[0] for p in self.trajectory]
        ys = [p[1] for p in self.trajectory]
        
        self.trajectory_line, = self.ax.plot(
            xs, ys, 'b-', linewidth=2.5, alpha=0.7, zorder=8
        )
        
        # 시작점
        self.ax.scatter(xs[0], ys[0], marker='s', s=100, c='green',
                       edgecolors='darkgreen', linewidths=2, zorder=9)
        
        # 궤적 점들도 표시
        if len(xs) > 2:
            self.ax.scatter(xs[1:-1], ys[1:-1], marker='.', s=40, 
                           c='lightblue', alpha=0.6, zorder=7)
    
    def show(self):
        """맵 표시"""
        plt.show()
        
    def save(self, filename: str = "trajectory_map.png"):
        """맵 저장"""
        self.fig.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"💾 맵 저장됨: {filename}")
        
    def save_trajectory(self, filename: str = None):
        """궤적 데이터 JSON으로 저장"""
        if filename is None:
            filename = TRAJECTORY_FILE
            
        data = {
            "timestamp": datetime.now().isoformat(),
            "origin": "7415 lower-left corner",
            "ap_count": len(ARUBA_APS),
            "trajectory": [
                {"x": x, "y": y, "time": t}
                for x, y, t in self.trajectory
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 궤적 데이터 저장됨: {filename}")
    
    def load_trajectory(self, filename: str = None):
        """궤적 데이터 로드"""
        if filename is None:
            filename = TRAJECTORY_FILE
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.trajectory = [
                (p["x"], p["y"], p["time"])
                for p in data["trajectory"]
            ]
            
            print(f"📂 궤적 데이터 로드됨: {len(self.trajectory)}개 포인트")
            return True
        except Exception as e:
            print(f"❌ 로드 실패: {e}")
            return False
    
    def clear_trajectory(self):
        """궤적 초기화"""
        self.trajectory = []
        self.current_position = None
        if self.trajectory_line:
            self.trajectory_line.remove()
            self.trajectory_line = None


def create_static_map(trajectory_data: List[Tuple[float, float]], 
                      output_file: str = "static/trajectory_map.png",
                      show_rooms: bool = True):
    """
    정적 궤적 맵 생성
    
    Args:
        trajectory_data: [(x, y), ...] 궤적 데이터
        output_file: 출력 파일명
        show_rooms: 호실 표시 여부
    """
    visualizer = MapVisualizer()
    visualizer.setup_map(show_rooms=show_rooms)
    
    # 궤적 그리기
    if len(trajectory_data) > 0:
        xs = [p[0] for p in trajectory_data]
        ys = [p[1] for p in trajectory_data]
        
        # 궤적 라인
        visualizer.ax.plot(xs, ys, 'b-', linewidth=2.5, alpha=0.7, label='이동 경로')
        
        # 시작점
        visualizer.ax.scatter(xs[0], ys[0], marker='s', s=150, c='green',
                            edgecolors='darkgreen', linewidths=2, 
                            zorder=10, label='시작점')
        
        # 끝점
        visualizer.ax.scatter(xs[-1], ys[-1], marker='o', s=200, c='lime',
                            edgecolors='darkgreen', linewidths=2,
                            zorder=10, label='현재 위치')
        
        # 중간 점들
        if len(xs) > 2:
            visualizer.ax.scatter(xs[1:-1], ys[1:-1], marker='.', s=40, 
                                c='lightblue', alpha=0.5, zorder=8)
    
    visualizer.ax.legend(loc='upper right')
    
    # 디렉토리 생성
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    visualizer.save(output_file)
    
    return visualizer


if __name__ == "__main__":
    print("=" * 60)
    print("🗺️ 맵 시각화 테스트 (7415 원점 기준)")
    print("=" * 60)
    
    # 맵 생성
    visualizer = MapVisualizer(figsize=(16, 8))
    visualizer.setup_map(show_rooms=True)
    
    # 테스트 궤적 (아래쪽 복도 → 위쪽 복도)
    import math
    
    test_trajectory = []
    
    # 아래쪽 복도를 따라 이동 (7415 → 7401)
    for i in range(15):
        x = 2 + i * 4  # 2m에서 시작, 4m씩 이동
        y = 3.5 + math.sin(i * 0.3) * 0.5  # 약간의 좌우 움직임
        test_trajectory.append((x, y))
    
    # 위쪽 복도로 이동
    for i in range(10):
        x = 58 - i * 2
        y = 3.5 + i * 1.3  # Y 방향으로 이동
        test_trajectory.append((x, y))
    
    # 위쪽 복도를 따라 이동
    for i in range(10):
        x = 38 + i * 3
        y = 16.5 + math.sin(i * 0.4) * 0.5
        test_trajectory.append((x, y))
    
    # 궤적 시각화
    for i, (x, y) in enumerate(test_trajectory):
        visualizer.update_position(x, y)
        
    print(f"\n📍 총 {len(test_trajectory)}개의 위치 포인트 표시")
    
    # 맵 저장
    os.makedirs("logs", exist_ok=True)
    visualizer.save("logs/test_trajectory_7415_origin.png")
    visualizer.save_trajectory("logs/test_trajectory.json")
    
    # 맵 표시
    visualizer.show()
