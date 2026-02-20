# 🤖 MAS — Multi-Agent System for Class Analysis

**멀티 에이전트 수업 분석 시스템** · 8개 AI 에이전트가 협업하여 수업 영상을 7차원 평가하는 플랫폼

[![Version](https://img.shields.io/badge/version-7.1.0-7c3aed)](https://github.com/edu-data/GAIM_Lab/releases/tag/v7.1)
[![Python](https://img.shields.io/badge/python-3.9+-3776AB)](https://python.org)
[![Gemini](https://img.shields.io/badge/Gemini_AI-4285F4)](https://ai.google.dev)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 📦 프로젝트 구성

| 리포지토리 | 설명 | 링크 |
| ---------- | ---- | ---- |
| **GAIM_Lab** | 수업 분석 핵심 시스템 (v7.1) | [edu-data/GAIM_Lab](https://github.com/edu-data/GAIM_Lab) |
| **GINUE 2035 발전계획** | 경인교대 AI 마이크로티칭 랩 운영 계획 | (본 리포지토리 내) |

---

## 🤖 GAIM Lab v7.1 주요 성과

| 지표 | 결과 |
| ---- | ---- |
| ✅ 분석 성공률 | **18/18 (100%)** |
| 📊 평균 점수 | **76.2점 (B+등급)** |
| 🏆 점수 범위 | **65.0 ~ 83.5점 (18.5pt)** |
| ⏱️ 처리 속도 | **영상당 ~5.5분** |
| 🗄️ 데이터 영속성 | **SQLite DB auto-save** |
| 📈 성장 분석 | **차원별 추세 + 자동 피드백** |

### v7.1 핵심 기능

- **Pedagogy Agent v7**: 구간화(Binning) 기반 결정론적 채점
- **Pydantic 계약**: SharedContext 타입 안전성 + 신뢰도 전파
- **SQLite 영속성**: analyses + dimension_scores CRUD
- **성장 분석기**: 차원별 선형 회귀 추세 + 규칙 기반 자동 피드백
- **History API**: `/history`, `/growth`, `/delete` 엔드포인트
- **실시간 코칭**: WebSocket 기반 실시간 수업 피드백
- **코호트 비교 분석**: 집단별 비교 분석 기능
- **성장 경로 로드맵**: 개인화된 성장 로드맵
- **Google OAuth**: Google 계정 인증
- **A/B 루브릭 실험**: 채점 기준 실험 프레임워크
- **PWA 지원**: Progressive Web App

---

## 🔗 관련 링크

| 링크 | 설명 |
| ---- | ---- |
| [MAS 홈페이지](https://edu-data.github.io/mas/mas-index.html) | 시스템 소개 |
| [MAS 대시보드](https://edu-data.github.io/mas/mas-dashboard.html) | 분석 결과 시각화 |
| [GAIM Lab 웹사이트](https://edu-data.github.io/GAIM_Lab/) | 프로모션 페이지 |
| [v7.1 릴리스](https://github.com/edu-data/GAIM_Lab/releases/tag/v7.1) | 최신 릴리스 |

---

## 📜 버전 히스토리

| 버전 | 날짜 | 주요 변경 |
| ---- | ---- | -------- |
| **v7.1** | 2026-02-20 | 실시간 코칭, 코호트 비교, 성장 로드맵, OAuth, A/B 루브릭, PWA |
| v7.0 | 2026-02-20 | Pydantic 계약, SQLite 영속성, 성장 분석, 하드코딩 경로 제거 |
| v6.0 | 2026-02-19 | 신뢰도·기준타당도 분석 도구 |
| v5.0 | 2026-02-18 | 화자 분리 & 담화 분석 |
| v4.0 | 2026-02-17 | MAS 멀티 에이전트 아키텍처 |
| v3.0 | 2026-02-05 | 웹 UI + 리포트 시스템 |
| v2.0 | 2026-02-05 | 배치 분석 + RAG 통합 |
| v1.0 | 2026-02-04 | 초기 시스템 |

---

<p align="center">
  <strong>경인교육대학교 GINUE AI Microteaching Lab</strong><br/>
  <a href="mailto:educpa@ginue.ac.kr">educpa@ginue.ac.kr</a> ·
  <a href="https://github.com/edu-data/mas">GitHub</a>
</p>
