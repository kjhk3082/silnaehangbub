"""
위치 추정 모듈
삼변측량(Trilateration) 및 가중 중심법을 사용한 실내 위치 추정
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.optimize import minimize
from config import (
    ARUBA_APS, AP_POSITIONS, rssi_to_distance,
    MIN_AP_FOR_TRILATERATION, MAX_DISTANCE,
    MAP_BOUNDS
)


class PositionEstimator:
    """
    실내 위치 추정 클래스
    여러 알고리즘을 지원:
    1. 가중 중심법 (Weighted Centroid)
    2. 삼변측량 (Trilateration)
    3. 최소제곱법 (Least Squares)
    """
    
    def __init__(self, method: str = "weighted_centroid"):
        """
        Args:
            method: 위치 추정 방법 ("weighted_centroid", "trilateration", "least_squares")
        """
        self.method = method
        self.last_position: Optional[Tuple[float, float]] = None
        self.position_history: List[Tuple[float, float, float]] = []  # (x, y, timestamp)
        
    def estimate(self, rssi_dict: Dict[str, float]) -> Optional[Tuple[float, float]]:
        """
        RSSI 값으로부터 위치 추정
        
        Args:
            rssi_dict: {AP이름: RSSI값} 딕셔너리
            
        Returns:
            (x, y) 좌표 또는 None
        """
        # RSSI를 거리로 변환
        distances = {}
        for ap_name, rssi in rssi_dict.items():
            if rssi > -100 and ap_name in AP_POSITIONS:
                dist = rssi_to_distance(rssi)
                if dist < MAX_DISTANCE:
                    distances[ap_name] = dist
        
        # 충분한 AP가 감지되지 않으면 None 반환
        if len(distances) < MIN_AP_FOR_TRILATERATION:
            print(f"⚠️ 감지된 AP 부족: {len(distances)}개 (최소 {MIN_AP_FOR_TRILATERATION}개 필요)")
            return self.last_position
        
        # 위치 추정 방법 선택
        if self.method == "weighted_centroid":
            position = self._weighted_centroid(distances)
        elif self.method == "trilateration":
            position = self._trilateration(distances)
        elif self.method == "least_squares":
            position = self._least_squares(distances)
        else:
            position = self._weighted_centroid(distances)
        
        # 맵 경계 내로 제한
        if position:
            x = max(MAP_BOUNDS["min_x"], min(position[0], MAP_BOUNDS["max_x"]))
            y = max(MAP_BOUNDS["min_y"], min(position[1], MAP_BOUNDS["max_y"]))
            position = (x, y)
            self.last_position = position
            
        return position
    
    def _weighted_centroid(self, distances: Dict[str, float]) -> Tuple[float, float]:
        """
        가중 중심법
        거리에 반비례하는 가중치로 위치 계산
        """
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        
        for ap_name, distance in distances.items():
            if distance > 0:
                # 거리에 반비례하는 가중치 (가까울수록 높은 가중치)
                weight = 1 / (distance ** 2)
                
                ap_x, ap_y = AP_POSITIONS[ap_name]
                weighted_x += ap_x * weight
                weighted_y += ap_y * weight
                total_weight += weight
        
        if total_weight > 0:
            return (weighted_x / total_weight, weighted_y / total_weight)
        return None
    
    def _trilateration(self, distances: Dict[str, float]) -> Optional[Tuple[float, float]]:
        """
        삼변측량법
        3개 이상의 원의 교점을 계산
        """
        # 가장 가까운 3개 AP 선택
        sorted_aps = sorted(distances.items(), key=lambda x: x[1])[:3]
        
        if len(sorted_aps) < 3:
            return self._weighted_centroid(distances)
        
        # 좌표 및 거리 추출
        points = []
        dists = []
        for ap_name, dist in sorted_aps:
            points.append(AP_POSITIONS[ap_name])
            dists.append(dist)
        
        # 삼변측량 계산
        try:
            x1, y1 = points[0]
            x2, y2 = points[1]
            x3, y3 = points[2]
            r1, r2, r3 = dists[0], dists[1], dists[2]
            
            # 선형화된 방정식 풀기
            A = 2 * np.array([
                [x2 - x1, y2 - y1],
                [x3 - x1, y3 - y1]
            ])
            
            b = np.array([
                r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2,
                r1**2 - r3**2 - x1**2 + x3**2 - y1**2 + y3**2
            ])
            
            # A가 특이행렬인지 확인
            if np.linalg.det(A) == 0:
                return self._weighted_centroid(distances)
            
            position = np.linalg.solve(A, b)
            return (float(position[0]), float(position[1]))
            
        except Exception as e:
            print(f"⚠️ 삼변측량 오류: {e}")
            return self._weighted_centroid(distances)
    
    def _least_squares(self, distances: Dict[str, float]) -> Tuple[float, float]:
        """
        최소제곱법
        모든 AP로부터의 거리 오차를 최소화하는 위치 찾기
        """
        def objective(pos):
            x, y = pos
            total_error = 0
            for ap_name, measured_dist in distances.items():
                ap_x, ap_y = AP_POSITIONS[ap_name]
                estimated_dist = math.sqrt((x - ap_x)**2 + (y - ap_y)**2)
                total_error += (estimated_dist - measured_dist) ** 2
            return total_error
        
        # 초기 추정값 (가중 중심)
        initial = self._weighted_centroid(distances)
        if initial is None:
            initial = (MAP_BOUNDS["max_x"] / 2, MAP_BOUNDS["max_y"] / 2)
        
        # 최적화
        result = minimize(objective, initial, method='Nelder-Mead')
        
        return (float(result.x[0]), float(result.x[1]))
    
    def add_to_history(self, x: float, y: float, timestamp: float):
        """위치 히스토리에 추가"""
        self.position_history.append((x, y, timestamp))
    
    def get_trajectory(self) -> List[Tuple[float, float, float]]:
        """궤적 데이터 반환"""
        return self.position_history.copy()
    
    def clear_history(self):
        """히스토리 초기화"""
        self.position_history = []
        self.last_position = None


def calculate_distance(pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
    """두 점 사이의 거리 계산"""
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)


if __name__ == "__main__":
    print("=" * 60)
    print("📍 위치 추정 모듈 테스트")
    print("=" * 60)
    
    # 테스트용 가상 RSSI 데이터
    # 사용자가 (30, 5) 위치에 있다고 가정
    test_rssi = {
        "AP-07": -75,  # 20m 거리
        "AP-09": -62,  # 8m 거리
        "AP-11": -58,  # 4m 거리
        "AP-12": -68,  # 16m 거리
        "AP-XX": -78,  # 28m 거리
        "AP-13": -85,  # 40m 거리
    }
    
    print("\n테스트 RSSI 값:")
    for ap, rssi in test_rssi.items():
        dist = rssi_to_distance(rssi)
        print(f"  {ap}: {rssi} dBm → {dist:.1f}m")
    
    # 각 방법으로 위치 추정
    methods = ["weighted_centroid", "trilateration", "least_squares"]
    
    print("\n위치 추정 결과:")
    for method in methods:
        estimator = PositionEstimator(method=method)
        position = estimator.estimate(test_rssi)
        if position:
            print(f"  {method}: ({position[0]:.2f}m, {position[1]:.2f}m)")
        else:
            print(f"  {method}: 추정 실패")
    
    print("\n실제 위치: (30.0m, 5.0m)")
