# 🏢 WiFi 기반 실내 위치 추적 시스템

> **한림대학교 자연과학관 4층 실내 항법 시스템**  
> WiFi RSSI 및 Fingerprinting 기반 실시간 위치 추적

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📋 목차

1. [프로젝트 개요](#-프로젝트-개요)
2. [시스템 아키텍처](#-시스템-아키텍처)
3. [핵심 기술 및 알고리즘](#-핵심-기술-및-알고리즘)
4. [설치 및 실행](#-설치-및-실행)
5. [주요 기능](#-주요-기능)
6. [API 명세](#-api-명세)
7. [활용 가능성](#-활용-가능성)
8. [향후 개선 계획](#-향후-개선-계획)
9. [프로젝트 구조](#-프로젝트-구조)

---

## 🎯 프로젝트 개요

### 배경
- GPS는 실내에서 작동하지 않음 (위성 신호 차단)
- 병원, 대학교 등 대형 건물에서 실내 위치 기반 서비스 필요성 증가
- 추가 인프라 없이 기존 WiFi AP를 활용한 저비용 솔루션 개발

### 목표
- **실시간 위치 추적**: 복도 내 현재 위치 파악
- **네비게이션**: 목적지(강의실) 안내
- **이동 분석**: 동선 기록 및 시각화

### 적용 환경
- **위치**: 한림대학교 자연과학관 4층
- **좌표계**: 7413호 앞 = 원점 (0m)
- **범위**: 약 65m 복도 (7413 ~ 7404)

---

## 🏗 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    웹 브라우저 (Client)                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ 추적화면 │  │ 분석화면 │  │ 캘리화면 │  │ Fingerprint 화면│ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └───────┬─────────┘ │
└───────┼────────────┼────────────┼───────────────┼───────────┘
        │            │            │               │
        ▼            ▼            ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask 서버 (web_track.py)                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    API Endpoints                        ││
│  │  /api/status  /api/start  /api/stop  /api/fingerprint  ││
│  └─────────────────────────────────────────────────────────┘│
│                            │                                 │
│  ┌─────────────────────────┴─────────────────────────────┐  │
│  │              위치 추정 엔진 (Hybrid)                    │  │
│  │  ┌──────────────────┐  ┌──────────────────────────┐   │  │
│  │  │ RSSI 기반 추정    │  │ Fingerprint 기반 추정     │   │  │
│  │  │ (1D 선형 보간)    │  │ (KNN 패턴 매칭)          │   │  │
│  │  └────────┬─────────┘  └────────────┬─────────────┘   │  │
│  │           │                         │                  │  │
│  │           └──────────┬──────────────┘                  │  │
│  │                      ▼                                 │  │
│  │            신뢰도 기반 결정 로직                         │  │
│  │         (FP ≥ 75% → FP, else → RSSI)                  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  macOS CoreWLAN Framework                    │
│              (WiFi RSSI 수집 - 연결된 AP + 주변 AP)           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔬 핵심 기술 및 알고리즘

### 1. RSSI 기반 1D 위치 추정 (Fallback)

연결된 WiFi AP의 신호 세기(RSSI)를 이용한 선형 보간법

```python
# 캘리브레이션 데이터 (위치, RSSI, 거리)
CALIBRATION = [
    ("7413", -44,  0.0),   # 원점
    ("STAIR", -50, 5.0),   # 계단
    ("EV", -54, 10.0),     # 엘리베이터
    ("7412", -58, 15.0),   # ...
]

# 선형 보간 공식
position = pos1 + (rssi - rssi1) * (pos2 - pos1) / (rssi2 - rssi1)
```

**특징:**
- 단순하고 빠름
- 1D 복도 환경에 적합
- RSSI 변동에 민감 → 스무딩 적용

### 2. WiFi Fingerprinting (주 측위 방식)

주변 AP들의 RSSI 패턴을 이용한 위치 추정

```python
# 패턴 수집 (위치별 RSSI 벡터)
7413: [-37, -39, -39, -40, -40, -41, -46, -49, ...]
7412: [-28, -29, -33, -43, -43, -43, -45, -46, ...]
EV:   [-28, -29, -29, -43, -43, -44, -46, -47, ...]

# KNN 알고리즘으로 가장 유사한 패턴 찾기
def estimate_location_knn(current_pattern, k=3):
    distances = []
    for loc, data in fingerprint_db.items():
        dist = euclidean_distance(current_pattern, data['pattern'])
        distances.append((loc, dist))
    
    # 상위 k개 후보의 가중 평균
    top_k = sorted(distances, key=lambda x: x[1])[:k]
    # 신뢰도 = 1 / (1 + 최소거리)
    confidence = 1 / (1 + top_k[0][1] / 10)
    return top_k[0][0], confidence
```

**macOS 제한사항 극복:**
- BSSID/SSID가 `<redacted>`로 가려짐 (개인정보 보호)
- **해결책**: RSSI 값만으로 패턴 생성 (정렬된 RSSI 벡터)

### 3. 신호 안정화 기법

```python
# RSSI 이동평균 (버퍼 크기: 10)
rssi_buffer = deque(maxlen=10)
smoothed_rssi = sum(rssi_buffer) / len(rssi_buffer)

# 위치 이동평균 (버퍼 크기: 8)
position_buffer = deque(maxlen=8)
smoothed_position = sum(position_buffer) / len(position_buffer)

# 최소 이동 거리 (노이즈 필터링)
MIN_POSITION_CHANGE = 1.0  # 1m 미만 이동 무시

# 방향 전환 임계값
DIRECTION_THRESHOLD = 5.0  # 5m 이상 이동시 방향 업데이트
```

### 4. 하이브리드 결정 로직

```python
# Fingerprint 신뢰도가 75% 이상이면 FP 사용
# 그렇지 않으면 RSSI 기반 위치 사용 (더 안정적)
if fp_confidence >= 0.75:
    method = "fingerprint"
    room = fp_location
else:
    method = "rssi"
    room = rssi_room
```

---

## 🚀 설치 및 실행

### 요구사항
- macOS (CoreWLAN 필요)
- Python 3.9+
- WiFi 연결 상태

### 설치

```bash
# 저장소 클론
git clone https://github.com/kjhk3082/silnaehangbub.git
cd silnaehangbub

# 의존성 설치
pip install -r requirements.txt
```

### 실행

```bash
# 웹 서버 실행
python web_track.py

# 브라우저에서 접속
open http://localhost:5001
```

### 페이지 구성

| URL | 설명 |
|-----|------|
| `/` | 메인 실시간 추적 화면 |
| `/analysis` | 데이터 분석 및 시각화 |
| `/calibrate` | RSSI 캘리브레이션 도구 |
| `/fingerprint` | Fingerprint 수집 도구 |

---

## 🎮 주요 기능

### 1. 실시간 위치 추적
- 현재 위치 (호실) 표시
- 복도 지도 위 위치 시각화
- RSSI 신호 세기 모니터링
- 측위 방식 표시 (FP/RSSI)

### 2. 강의실 찾기 네비게이션
- 목적지 강의실 선택
- 현재 위치 → 목적지 방향 안내
- 남은 거리 표시
- 도착 알림

### 3. 이동 데이터 분석
- **위치 변화 그래프**: 시간에 따른 위치 변화
- **RSSI 그래프**: 신호 세기 변화
- **속도 그래프**: 이동 속도 분석
- **체류 시간**: 호실별 머문 시간
- **히트맵**: 자주 지나간 구간

### 4. 데이터 내보내기
- JSON 다운로드
- CSV 변환
- 그래프별 PNG 저장
- 전체 리포트 PDF 출력

---

## 📡 API 명세

### 상태 조회
```
GET /api/status
```
```json
{
  "rssi": -40,
  "room": "7413",
  "position": 0.0,
  "method": "rssi",
  "fingerprint": {
    "location": "7408",
    "confidence": 0.6,
    "candidates": [...]
  },
  "rssi_fallback": {
    "room": "7413",
    "position": 0.0
  }
}
```

### 추적 시작/정지
```
POST /api/start
POST /api/stop
```

### Fingerprint 수집
```
POST /api/fingerprint/collect
Content-Type: application/json
{"location": "7413", "samples": 20}
```

### 데이터 저장/조회
```
POST /api/save
GET /api/list
GET /api/load/<filename>
```

---

## 💡 활용 가능성

### 1. 의료/병원 환경
- **환자 위치 추적**: 치매 환자, 수술 대기 환자 위치 파악
- **의료진 동선 분석**: 업무 효율성 분석
- **응급 상황 대응**: 가장 가까운 의료진 호출
- **자산 추적**: 휠체어, 침대, 의료기기 위치 관리

### 2. 대학교/교육시설
- **강의실 찾기**: 신입생, 방문객 안내
- **출석 체크**: 위치 기반 자동 출석
- **시설 이용 분석**: 혼잡도 파악, 공간 활용 최적화

### 3. 상업/리테일
- **고객 동선 분석**: 매장 레이아웃 최적화
- **맞춤형 광고**: 위치 기반 프로모션
- **재고 관리**: 물품 위치 추적

### 4. 스마트 빌딩
- **에너지 관리**: 점유 기반 공조/조명 제어
- **보안**: 비인가 구역 접근 감지
- **비상 대피**: 대피 경로 안내

---

## 🔮 향후 개선 계획

### 단기 (1-2개월)

| 항목 | 설명 | 난이도 |
|-----|------|-------|
| **다층 지원** | 층간 이동 감지 (기압센서 연동) | ⭐⭐ |
| **Fingerprint 자동 갱신** | 일정 기간마다 패턴 재수집 | ⭐⭐ |
| **오프라인 모드** | 서버 없이 로컬 추적 | ⭐⭐⭐ |

### 중기 (3-6개월)

| 항목 | 설명 | 난이도 |
|-----|------|-------|
| **BLE Beacon 연동** | 추가 AP 없이 정밀도 향상 | ⭐⭐⭐ |
| **머신러닝 적용** | RSSI → 위치 예측 신경망 | ⭐⭐⭐⭐ |
| **크로스 플랫폼** | iOS/Android 앱 개발 | ⭐⭐⭐⭐ |

### 장기 (6개월+)

| 항목 | 설명 | 난이도 |
|-----|------|-------|
| **UWB 통합** | 센티미터급 정밀 측위 | ⭐⭐⭐⭐⭐ |
| **AR 네비게이션** | 증강현실 길안내 | ⭐⭐⭐⭐⭐ |
| **다중 사용자** | 여러 명 동시 추적 | ⭐⭐⭐⭐ |

### 기술적 개선사항

```
1. Fingerprint 개선
   - Weighted KNN 적용
   - 시간대별 패턴 (사람 밀집도 변화 반영)
   - 패턴 클러스터링으로 유사 위치 그룹화

2. 신호 처리 개선
   - 칼만 필터 적용 (노이즈 제거)
   - 파티클 필터 (확률적 위치 추정)
   - RSSI → 거리 변환 모델 개선

3. 사용성 개선
   - 음성 안내
   - 진동 피드백
   - 시각장애인 접근성
```

---

## 📁 프로젝트 구조

```
silnaehangbub/
├── 📄 web_track.py          # 메인 Flask 서버
├── 📄 fingerprint_engine.py # Fingerprint 수집/추정 엔진
├── 📄 wifi_scanner.py       # WiFi RSSI 수집 (CoreWLAN)
├── 📄 calibrate.py          # 터미널 캘리브레이션 도구
├── 📄 config.py             # 설정 (AP 정보 등)
├── 📄 requirements.txt      # 의존성
├── 📄 README.md             # 프로젝트 문서
│
├── 📁 templates/            # HTML 템플릿
│   ├── track.html           # 메인 추적 화면
│   ├── analysis.html        # 분석 대시보드
│   ├── calibrate.html       # 웹 캘리브레이션
│   └── fingerprint.html     # Fingerprint 수집
│
├── 📁 logs/                 # 데이터 저장
│   ├── fingerprint_db.json  # Fingerprint DB
│   └── track_*.json         # 추적 기록
│
├── 📁 res/                  # 결과물
│   ├── *.png                # 그래프 이미지
│   └── *.pdf                # 리포트
│
└── 📁 room/                 # 공간 정보
    └── rooms_coords.json    # 호실 좌표
```

---

## 📊 성능 지표

| 지표 | 값 | 비고 |
|-----|---|------|
| 평균 오차 | ~3-5m | 복도 환경 |
| 호실 정확도 | ~80% | 인접 호실 혼동 가능 |
| 갱신 주기 | 0.5초 | 실시간 |
| 응답 시간 | <100ms | API 응답 |

---

## 🤝 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 👨‍💻 개발자

- **김코** - 한림대학교 의료AI 현장중심 실무 수업 기말 프로젝트

---

## 🙏 감사의 말

- 한림대학교 자연과학관 WiFi 인프라
- Flask, Chart.js 오픈소스 커뮤니티
- 김동현 교수님 지도

---

*Last Updated: 2025-12-19*
