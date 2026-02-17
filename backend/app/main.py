"""
GAIM Lab - FastAPI 메인 애플리케이션
GINUE AI Microteaching Lab 백엔드 서버
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api import analysis, portfolio, badges, mentoring, realtime, agents

# 앱 초기화
app = FastAPI(
    title="GAIM Lab API",
    description="GINUE AI Microteaching Lab - 예비교원 수업역량 강화 시스템",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
UPLOAD_DIR = Path("D:/AI/GAIM_Lab/uploads")
OUTPUT_DIR = Path("D:/AI/GAIM_Lab/output")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# 라우터 등록
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["분석"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["포트폴리오"])
app.include_router(badges.router, prefix="/api/v1/badges", tags=["디지털 배지"])
app.include_router(mentoring.router, prefix="/api/v1/mentoring", tags=["멘토링"])
app.include_router(realtime.router, prefix="/api/v1", tags=["실시간"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["에이전트"])


@app.get("/")
async def root():
    """서버 상태 확인"""
    return {
        "name": "GAIM Lab API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/api/docs",
            "analysis": "/api/v1/analysis",
            "portfolio": "/api/v1/portfolio",
            "badges": "/api/v1/badges",
            "mentoring": "/api/v1/mentoring"
        }
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}
