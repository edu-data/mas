"""
GAIM Lab - 포트폴리오 API 엔드포인트
학생별 수업 역량 포트폴리오 관리
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
import uuid

router = APIRouter()

# 인메모리 포트폴리오 저장소
portfolio_store: Dict[str, Dict] = {}


class StudentProfile(BaseModel):
    """학생 프로필"""
    student_id: str
    name: str
    department: str
    year: int
    email: Optional[str] = None


class SessionRecord(BaseModel):
    """수업 시연 세션 기록"""
    session_id: str
    date: str
    video_name: str
    total_score: float
    grade: str
    dimensions: List[Dict]
    feedback_summary: str


class PortfolioSummary(BaseModel):
    """포트폴리오 요약"""
    student_id: str
    name: str
    total_sessions: int
    average_score: float
    best_score: float
    improvement_rate: float
    badges: List[str]


@router.post("/", response_model=StudentProfile)
async def create_portfolio(profile: StudentProfile):
    """새 포트폴리오 생성"""
    if profile.student_id in portfolio_store:
        raise HTTPException(status_code=400, detail="이미 존재하는 학생 ID입니다")
    
    portfolio_store[profile.student_id] = {
        "profile": profile.dict(),
        "sessions": [],
        "badges": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    return profile


@router.get("/{student_id}", response_model=PortfolioSummary)
async def get_portfolio(student_id: str):
    """학생 포트폴리오 조회"""
    if student_id not in portfolio_store:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없습니다")
    
    portfolio = portfolio_store[student_id]
    sessions = portfolio["sessions"]
    
    if sessions:
        scores = [s["total_score"] for s in sessions]
        avg_score = sum(scores) / len(scores)
        best_score = max(scores)
        
        # 개선율: 첫 3개 평균 vs 마지막 3개 평균
        if len(scores) >= 6:
            first_avg = sum(scores[:3]) / 3
            last_avg = sum(scores[-3:]) / 3
            improvement_rate = ((last_avg - first_avg) / first_avg) * 100
        else:
            improvement_rate = 0
    else:
        avg_score = 0
        best_score = 0
        improvement_rate = 0
    
    return PortfolioSummary(
        student_id=student_id,
        name=portfolio["profile"]["name"],
        total_sessions=len(sessions),
        average_score=round(avg_score, 1),
        best_score=round(best_score, 1),
        improvement_rate=round(improvement_rate, 1),
        badges=portfolio["badges"]
    )


@router.get("/{student_id}/sessions")
async def get_sessions(student_id: str, limit: int = 10):
    """학생의 수업 시연 세션 목록"""
    if student_id not in portfolio_store:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없습니다")
    
    sessions = portfolio_store[student_id]["sessions"]
    
    return {
        "student_id": student_id,
        "total": len(sessions),
        "sessions": sessions[-limit:][::-1]  # 최신순
    }


@router.post("/{student_id}/sessions")
async def add_session(student_id: str, analysis_id: str):
    """
    분석 결과를 포트폴리오 세션에 추가
    
    - **analysis_id**: 완료된 분석 ID
    """
    if student_id not in portfolio_store:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없습니다")
    
    # 분석 결과 연동 (analysis_store에서 가져오기)
    from app.api.analysis import analysis_store
    
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")
    
    analysis = analysis_store[analysis_id]
    
    if analysis["status"] != "completed":
        raise HTTPException(status_code=400, detail="완료된 분석만 추가할 수 있습니다")
    
    result = analysis["result"]["gaim_evaluation"]
    
    session = {
        "session_id": str(uuid.uuid4()),
        "analysis_id": analysis_id,
        "date": datetime.now().isoformat(),
        "video_name": analysis["video_name"],
        "total_score": result["total_score"],
        "grade": result["grade"],
        "dimensions": result["dimensions"],
        "feedback_summary": result["overall_feedback"]
    }
    
    portfolio_store[student_id]["sessions"].append(session)
    portfolio_store[student_id]["updated_at"] = datetime.now().isoformat()
    
    # 배지 자동 부여 체크
    await _check_and_award_badges(student_id)
    
    return {"message": "세션이 추가되었습니다", "session": session}


@router.get("/{student_id}/progress")
async def get_progress(student_id: str):
    """학생의 차원별 진척도"""
    if student_id not in portfolio_store:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없습니다")
    
    sessions = portfolio_store[student_id]["sessions"]
    
    if not sessions:
        return {"message": "세션 데이터가 없습니다", "progress": []}
    
    # 차원별 점수 추적
    dimension_progress = {}
    
    for session in sessions:
        for dim in session["dimensions"]:
            dim_name = dim["name"]
            if dim_name not in dimension_progress:
                dimension_progress[dim_name] = []
            dimension_progress[dim_name].append({
                "date": session["date"],
                "score": dim["score"],
                "percentage": dim["percentage"]
            })
    
    return {
        "student_id": student_id,
        "total_sessions": len(sessions),
        "dimension_progress": dimension_progress
    }


async def _check_and_award_badges(student_id: str):
    """배지 자동 부여 체크"""
    portfolio = portfolio_store[student_id]
    sessions = portfolio["sessions"]
    current_badges = portfolio["badges"]
    
    # 첫 수업 배지
    if len(sessions) == 1 and "first_session" not in current_badges:
        current_badges.append("first_session")
    
    # 5회 완료 배지
    if len(sessions) >= 5 and "five_sessions" not in current_badges:
        current_badges.append("five_sessions")
    
    # 80점 이상 달성 배지
    if any(s["total_score"] >= 80 for s in sessions) and "score_80" not in current_badges:
        current_badges.append("score_80")
    
    # 90점 이상 달성 배지
    if any(s["total_score"] >= 90 for s in sessions) and "score_90" not in current_badges:
        current_badges.append("score_90")
    
    # 꾸준한 개선 배지 (3회 연속 점수 상승)
    if len(sessions) >= 3:
        scores = [s["total_score"] for s in sessions[-3:]]
        if all(scores[i] < scores[i+1] for i in range(2)) and "consistent_improvement" not in current_badges:
            current_badges.append("consistent_improvement")


@router.get("/{student_id}/export/pdf")
async def export_portfolio_pdf(student_id: str):
    """
    포트폴리오 PDF 내보내기
    
    학생의 전체 포트폴리오를 PDF로 생성하여 다운로드 링크 반환
    """
    from fastapi.responses import FileResponse
    from app.services.report_generator import GAIMReportGenerator
    
    if student_id not in portfolio_store:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없습니다")
    
    portfolio = portfolio_store[student_id]
    sessions = portfolio["sessions"]
    
    # 배지 정보 매핑
    badge_info = {
        "first_session": {"name": "첫 수업 시연", "icon": "🎬"},
        "five_sessions": {"name": "꾸준한 연습", "icon": "🔄"},
        "score_80": {"name": "우수 수업", "icon": "⭐"},
        "score_90": {"name": "최우수 수업", "icon": "🏆"},
        "consistent_improvement": {"name": "꾸준한 성장", "icon": "📈"}
    }
    
    badges_data = []
    for badge_id in portfolio["badges"]:
        info = badge_info.get(badge_id, {"name": badge_id, "icon": "🏅"})
        badges_data.append({
            "badge_id": badge_id,
            "name": info["name"],
            "icon": info["icon"],
            "earned_at": portfolio.get("updated_at", "")[:10]
        })
    
    # 세션 데이터 변환 (dimensions 구조 맞추기)
    formatted_sessions = []
    for s in sessions:
        dims = []
        for d in s.get("dimensions", []):
            dims.append({
                "name": d.get("name", ""),
                "score": d.get("score", 0),
                "max": d.get("max_score", 20)
            })
        formatted_sessions.append({
            "date": s.get("date", "")[:10],
            "total_score": s.get("total_score", 0),
            "grade": s.get("grade", "-"),
            "dimensions": dims
        })
    
    portfolio_data = {
        "student": {
            "name": portfolio["profile"]["name"],
            "student_id": student_id
        },
        "sessions": formatted_sessions,
        "badges": badges_data
    }
    
    generator = GAIMReportGenerator()
    report_path = generator.generate_portfolio_html(portfolio_data)
    
    return {
        "message": "포트폴리오 리포트가 생성되었습니다",
        "html_path": report_path,
        "download_url": f"/output/{report_path.split('/')[-1]}"
    }


@router.get("/{student_id}/export/demo")
async def export_portfolio_demo():
    """
    데모 포트폴리오 PDF 내보내기
    """
    from app.services.report_generator import GAIMReportGenerator
    
    # 데모 데이터
    demo_data = {
        "student": {
            "name": "김예비",
            "student_id": "demo_student"
        },
        "sessions": [
            {
                "date": "2026-01-15", "total_score": 72, "grade": "C+",
                "dimensions": [
                    {"name": "수업 전문성", "score": 12, "max": 20},
                    {"name": "교수학습 방법", "score": 13, "max": 20},
                    {"name": "판서 및 언어", "score": 10, "max": 15},
                    {"name": "수업 태도", "score": 11, "max": 15},
                    {"name": "학생 참여", "score": 10, "max": 15},
                    {"name": "시간 배분", "score": 7, "max": 10},
                    {"name": "창의성", "score": 3, "max": 5}
                ]
            },
            {
                "date": "2026-02-05", "total_score": 85, "grade": "B+",
                "dimensions": [
                    {"name": "수업 전문성", "score": 16, "max": 20},
                    {"name": "교수학습 방법", "score": 17, "max": 20},
                    {"name": "판서 및 언어", "score": 13, "max": 15},
                    {"name": "수업 태도", "score": 13, "max": 15},
                    {"name": "학생 참여", "score": 13, "max": 15},
                    {"name": "시간 배분", "score": 8, "max": 10},
                    {"name": "창의성", "score": 4, "max": 5}
                ]
            }
        ],
        "badges": [
            {"name": "첫 수업 시연", "icon": "🎬", "earned_at": "2026-01-15"},
            {"name": "우수 수업", "icon": "⭐", "earned_at": "2026-02-05"},
            {"name": "10% 성장", "icon": "📈", "earned_at": "2026-02-05"}
        ]
    }
    
    generator = GAIMReportGenerator()
    report_path = generator.generate_portfolio_html(demo_data)
    
    return {
        "message": "데모 포트폴리오 리포트가 생성되었습니다",
        "html_path": report_path,
        "download_url": f"/output/{report_path.split('/')[-1]}"
    }

