# 🤖 MAS — Multi-Agent System for Class Analysis

**멀티 에이전트 수업 분석 시스템** · 8개 AI 에이전트가 협업하여 수업 영상을 7차원 평가하는 플랫폼

[![Version](https://img.shields.io/badge/version-5.0.0-7c3aed)](https://github.com/edu-data/mas/releases/tag/v5.0)
[![Python](https://img.shields.io/badge/python-3.9+-3776AB)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_18-61DAFB)](https://react.dev)
[![Gemini](https://img.shields.io/badge/Gemini_AI-4285F4)](https://ai.google.dev)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

<p align="center">
  <a href="https://edu-data.github.io/mas/docs/mas-index.html"><strong>🌐 홈페이지</strong></a> ·
  <a href="https://edu-data.github.io/mas/docs/mas-dashboard.html"><strong>📊 대시보드</strong></a> ·
  <a href="https://github.com/edu-data/mas/releases/tag/v4.0"><strong>📦 릴리스</strong></a>
</p>

---

## 🎯 프로젝트 소개

MAS(Multi-Agent System)는 **예비교원의 수업 영상**을 8개 전문화된 AI 에이전트가 **병렬·순차 파이프라인**으로 분석하여, 초등학교 임용 2차 수업실연 기준에 따라 **7차원 100점 만점**으로 자동 평가하는 시스템입니다.

### 주요 성과

| 지표 | 결과 |
| ---- | ---- |
| ✅ 분석 성공률 | **18/18 (100%)** |
| 📊 평균 점수 | **77.4점 (B+등급)** |
| 🏆 점수 범위 | **69.7 ~ 83.2점 (13.5pt)** |
| ⏱️ 총 처리 시간 | **114.9분 (영상당 ~6.4분)** |
| 🤖 에이전트 수 | **8개** |
| 📐 평가 차원 | **7개** |
| 🗣️ 화자 분리 | **v5.0 NEW** |

---

## 🔗 에이전트 파이프라인

```
┌─────────────┐
│  Extractor   │  GPU 가속 FFmpeg 프레임/오디오 추출
└──────┬──────┘
       │
  ┌────┴────────────────────────┐
  │         병렬 실행             │
  ├──────────┬─────────┬────────┤
  │ Vision   │ Content │  STT   │  시각/콘텐츠/음성 분석
  │ Agent    │ Agent   │ Agent  │
  └────┬─────┴────┬────┴───┬───┘
       └──────────┼────────┘
                  │
          ┌───────┴───────┐
          │  Vibe Agent   │  프로소디(억양·속도·에너지) 분석
          └───────┬───────┘
          ┌───────┴───────┐
          │ Pedagogy Agent│  교육학 7차원 체계적 평가
          └───────┬───────┘
          ┌───────┴───────┐
          │ Feedback Agent│  LLM + 규칙 기반 맞춤형 피드백
          └───────┬───────┘
          ┌───────┴───────┐
          │ Master Agent  │  종합 보고서 생성
          └───────────────┘
```

---

## 🤖 8개 AI 에이전트

| # | 에이전트 | 역할 | 핵심 기술 |
| - | ------- | ---- | -------- |
| 1 | **Extractor** | 영상에서 프레임·오디오 초고속 추출 | FFmpeg CUDA, GPU 가속 |
| 2 | **Vision** | 교사 시선, 제스처, 자세 비언어적 분석 | OpenCV, Gemini Vision |
| 3 | **Content** | 판서, 교수자료, 멀티미디어 콘텐츠 분석 | Gemini AI |
| 4 | **STT** | 음성→텍스트 변환, 한국어 필러 감지 | OpenAI Whisper |
| 5 | **Vibe** | 음성 프로소디(억양·속도·에너지) 분석 | Librosa |
| 6 | **Pedagogy** | 교육학 이론 기반 7차원 체계적 평가 | RAG + Gemini |
| 7 | **Feedback** | 개인 맞춤형 피드백·액션 플랜 생성 | LLM + Rule Engine |
| 8 | **Master** | 전체 결과 종합, 최종 보고서 생성 | Gemini AI |

---

## 📐 7차원 평가 프레임워크

초등학교 임용 2차 수업실연 평가 기준 기반 **100점 만점** 체계:

| 차원 | 배점 | 평가 영역 |
| ---- | :--: | -------- |
| 수업 전문성 | 20점 | 학습목표 명료성, 학습내용 충실성 |
| 교수학습 방법 | 20점 | 교수법 다양성, 학습활동 효과성 |
| 판서 및 언어 | 15점 | 판서 가독성, 언어 명료성, 발화속도 |
| 수업 태도 | 15점 | 교사 열정, 학생 소통, 자신감 |
| 학생 참여 | 15점 | 질문 기법, 피드백 제공 |
| 시간 배분 | 10점 | 수업 단계별 시간 균형 |
| 창의성 | 5점 | 수업 기법의 창의성 |

---

## 🏗️ 시스템 구조

```
MAS/
├── core/                        # 🧠 분석 엔진
│   ├── agents/                  # 8개 AI 에이전트
│   │   ├── orchestrator.py      # AgentOrchestrator (파이프라인 관리)
│   │   ├── vision_agent.py      # 비전 분석
│   │   ├── content_agent.py     # 콘텐츠 분석
│   │   ├── stt_agent.py         # 음성 인식
│   │   ├── vibe_agent.py        # 프로소디 분석
│   │   ├── pedagogy_agent.py    # 교육학 평가
│   │   ├── feedback_agent.py    # 피드백 생성
│   │   └── master_agent.py      # 종합 보고서
│   └── analyzers/               # 기반 분석 모듈
│       ├── timelapse_analyzer.py # FFmpeg 프레임 추출
│       └── audio_analyzer.py    # 오디오 처리
├── backend/                     # ⚡ FastAPI 백엔드
│   └── app/
│       ├── api/                 # REST API + 에이전트 모니터링
│       ├── core/                # RAG, Gemini 평가기
│       └── services/            # 리포트 생성
├── frontend/                    # 💻 React 18 + Vite
│   └── src/
│       ├── components/          # UI 컴포넌트
│       └── pages/               # AgentMonitor, Dashboard 등
├── docs/                        # 📄 GitHub Pages
├── run_batch_agents.py          # 🔄 배치 분석 (MAS 파이프라인)
├── run_sample_analysis.py       # 🔬 단일 영상 분석
└── pyproject.toml               # 📦 패키지 설정
```

---

## 🚀 시작하기

### 필수 요구사항

- **Python** 3.9+
- **Node.js** 18+
- **FFmpeg** (CUDA GPU 가속 권장)
- **Google Gemini API Key**

### 설치 및 실행

```bash
# 1. 저장소 클론
git clone https://github.com/edu-data/mas.git
cd mas

# 2. 환경변수 설정
export GOOGLE_API_KEY="your-gemini-api-key"

# 3. Backend 실행
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. Frontend 실행 (새 터미널)
cd frontend
npm install
npm run dev
```

### 분석 실행

```bash
# 단일 영상 분석
python run_sample_analysis.py video/sample.mp4

# 배치 분석 (MAS 파이프라인)
python run_batch_agents.py

# 레거시 배치 분석
python batch_analysis.py --limit 5
```

---

## 🔗 API 엔드포인트

### 분석 API

| Method | 엔드포인트 | 설명 |
| ------ | --------- | ---- |
| POST | `/api/v1/analysis/upload` | 영상 업로드 |
| POST | `/api/v1/analysis/analyze` | 분석 시작 |
| GET | `/api/v1/analysis/{id}` | 분석 결과 조회 |

### 에이전트 모니터링 API

| Method | 엔드포인트 | 설명 |
| ------ | --------- | ---- |
| POST | `/api/v1/agents/start` | MAS 파이프라인 시작 |
| GET | `/api/v1/agents/status/{id}` | 에이전트 상태 조회 |
| GET | `/api/v1/agents/events/{id}` | 이벤트 히스토리 조회 |

### 배치·포트폴리오

| Method | 엔드포인트 | 설명 |
| ------ | --------- | ---- |
| POST | `/api/v1/analysis/batch/start` | 배치 분석 시작 |
| GET | `/api/v1/analysis/batch/{id}` | 배치 상태 조회 |
| GET | `/api/v1/portfolio` | 포트폴리오 조회 |
| GET | `/api/v1/badges` | 디지털 배지 목록 |

---

## 📊 분석 결과

### 🤖 MAS v5.0 — 18개 영상 분석 (최신)

| 통계 | 결과 |
| ---- | ---- |
| ✅ 성공률 | **18/18 (100%)** |
| 📊 평균 점수 | **77.4점 (B+등급)** |
| 🏆 최고 점수 | **83.2점 (20251209_141700, A-등급)** |
| 📉 최저 점수 | **69.7점 (20251209_150303, B-등급)** |
| 📏 점수 범위 | **13.5pt (v4.2 대비 1.4배 확대)** |
| ⏱️ 총 처리 시간 | **114.9분** |

**등급 분포**: A-등급 4개 (22%) / B+등급 11개 (61%) / B등급 2개 (11%) / B-등급 1개 (6%)

**차원별 평균 성취율**:

| 차원 | 평균 | 성취율 |
| ---- | :--: | :--: |
| 학생 참여 | 14.7/15 | **98%** |
| 수업 전문성 | 15.4/20 | 77% |
| 판서 및 언어 | 11.1/15 | 74% |
| 교수학습 방법 | 14.6/20 | 73% |
| 수업 태도 | 10.9/15 | 73% |
| 시간 배분 | 7.1/10 | 71% |
| 창의성 | 3.5/5 | 70% |

| 대시보드 | 링크 |
| -------- | ---- |
| 🤖 MAS 홈페이지 | [edu-data.github.io/mas](https://edu-data.github.io/mas/docs/mas-index.html) |
| 📊 v5.0 분석 대시보드 | [18개 영상 시각화 + 화자 분리](https://edu-data.github.io/GAIM_Lab/batch_dashboard.html) |
| 📊 MAS 대시보드 | [v4.2 분석 결과](https://edu-data.github.io/mas/docs/mas-dashboard.html) |

### 📋 이전 버전 분석 결과

| 보고서 | 설명 |
| ------ | ---- |
| [v5.0 배치 대시보드](https://edu-data.github.io/GAIM_Lab/batch_dashboard.html) | v5.0 화자분리·점수분포·산점도 |
| [최고점 리포트](https://edu-data.github.io/GAIM_Lab/best_report_110545.html) | 84점 영상 상세 분석 |
| [FIAS 대시보드](https://edu-data.github.io/GAIM_Lab/fias-dashboard.html) | Flanders 상호작용 분석 |
| [종합 평가 보고서](https://edu-data.github.io/GAIM_Lab/comprehensive_report.html) | 18개 영상 종합 분석 |
| [GAIM Lab 웹사이트](https://edu-data.github.io/GAIM_Lab/) | 시스템 소개 |

---

## 📜 버전 히스토리 (Changelog)

### v5.0 — 화자 분리 & 담화 분석 `2026-02-18`

- **Discourse Analyzer** 신규 추가: STT 결과에서 교사/학생 발화를 분리하여 담화 패턴 분석
- 교사 발화 비율, 학생 발화 횟수, 질문 유형 자동 분류
- v5.0 배치 대시보드: 화자 분리 산점도 차트 (교사비율 vs 총점, 학생발화 vs 총점)
- 점수 범위 확대: v4.2 **9.7pt** → v5.0 **13.5pt** (1.4배)
- 등급분포 개선: A-:4 / B+:11 / B:2 / B-:1
- 평균 점수: **77.4점** (v4.2 대비 +0.4pt)

### v4.2 — 에이전트 버그 수정 `2026-02-18`

- **Vision/Content 프레임 경로 버그 수정**: `flash_extract_resources`가 `{temp_dir}/frame_*.jpg`에 저장하지만, 오케스트레이터가 `{temp_dir}/frames/`에서 검색하던 경로 불일치 해결
- Vision Agent 0.02s → **5.24s** (얼굴감지·제스처·움직임 실분석)
- Content Agent 0.0s → **161.3s** (OCR·슬라이드·텍스트밀도 실분석)
- `_phase_synthesize`에 vision/content/vibe 요약 데이터 추가
- 배치 재분석 결과: 평균 **77.0점**, 등급분포 A-:2 / B+:13 / B:3

### v4.1 — 점수 차별화 강화 `2026-02-18`

- `pedagogy_agent.py` 전면 리팩토링
- `_safe()` 헬퍼로 에이전트 에러/빈 데이터 안전 처리
- STT 데이터 기반 7차원 전체 차별화 강화
- 한국어 발화속도 기준 보정 (3.0~5.0 음절/초)
- 점수 범위 **71.5~82.6** (11pt range, 이전 44.9~53.4에서 대폭 개선)
- 등급분포 A- 11개 / B+ 4개 / B 3개

### v4.0 — MAS 멀티 에이전트 시스템 `2026-02-17`

- **AgentOrchestrator** 파이프라인 아키텍처 도입
- 8개 AI 에이전트 설계 및 구현 (Extractor, Vision, Content, STT, Vibe, Pedagogy, Feedback, Master)
- `SharedContext` 에이전트 간 데이터 공유 프레임워크
- Event-driven Pub/Sub 메시지 버스
- MAS 전용 홈페이지 (`mas-index.html`) 및 대시보드 (`mas-dashboard.html`)
- 18개 영상 배치 분석 자동화 (`run_batch_agents.py`)

### v3.0 — 웹 UI 및 리포트 시스템 `2026-02-05`

- **FastAPI 백엔드** + **React 18 프론트엔드** 풀스택 구현
- 학생 포트폴리오 레이더 차트·성장 추적·디지털 배지 시스템
- 실시간 분석 진행 피드백 UI
- 모의수업 영상 분석 자동화 및 HTML/PDF 리포트 생성
- E2E 테스트 (Vitest + Playwright)

### v2.0 — 배치 분석 및 RAG 통합 `2026-02-05`

- **배치 분석 시스템** (`batch_analysis.py`): 18개 영상 순차 처리, CSV 요약
- **RAG 파이프라인**: Vertex AI Search + 교육학 지식 베이스 통합
- 리포트 v2: QR코드 삽입, 반응형 차트
- FIAS(Flanders 상호작용 분석) 대시보드 추가
- 배치 대시보드 (점수분포·등급·레이더차트 시각화)

### v1.0 — 초기 시스템 `2026-02-04`

- **GAIM Lab 영상 분석 시스템** 초기 아키텍처 설계
- `TimeLapseAnalyzer` 영상 프레임 추출 및 분석
- `GAIMLectureEvaluator` 7차원 100점 만점 평가 프레임워크 구현
- `GAIMReportGenerator` HTML 리포트 생성
- GPU 가속 FFmpeg 프레임 추출 구현
- 병렬 프레임 분석 (`ParallelFrameAnalyzer`) 멀티프로세싱 최적화
- GitHub Pages 프로모션 랜딩 페이지

---

## ⚙️ 기술 스택

| 영역 | 기술 |
| ---- | ---- |
| **AI/ML** | Google Gemini AI, OpenAI Whisper, OpenCV, Librosa |
| **Backend** | FastAPI, Python 3.9+, RAG Pipeline |
| **Frontend** | React 18, Vite, Chart.js |
| **영상 처리** | FFmpeg (CUDA GPU 가속) |
| **아키텍처** | Event-driven AgentOrchestrator, Pub/Sub MessageBus |
| **배포** | GitHub Pages, GitHub Actions |

---

## 🧪 테스트

```bash
# Frontend 단위 테스트
cd frontend && npm test

# E2E 테스트
npm run test:e2e

# RAG 파이프라인 테스트
python test_rag_pipeline.py
```

---

## 📄 라이선스

MIT License · 경인교육대학교 GAIM Lab

---

<p align="center">
  <strong>경인교육대학교 GINUE AI Microteaching Lab</strong><br/>
  <a href="mailto:educpa@ginue.ac.kr">educpa@ginue.ac.kr</a> ·
  <a href="https://github.com/edu-data/mas">GitHub</a> ·
  <a href="https://edu-data.github.io/mas/docs/mas-index.html">웹사이트</a>
</p>
