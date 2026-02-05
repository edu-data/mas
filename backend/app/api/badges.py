"""
GAIM Lab - 디지털 배지 API 엔드포인트
수업 역량 인증 배지 관리
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

router = APIRouter()

# 배지 정의
BADGE_DEFINITIONS = {
    "first_session": {
        "name": "첫 수업 시연",
        "description": "GAIM Lab에서 첫 번째 마이크로티칭을 완료했습니다",
        "icon": "🎬",
        "category": "milestone",
        "points": 10
    },
    "five_sessions": {
        "name": "꾸준한 연습",
        "description": "5회의 마이크로티칭 세션을 완료했습니다",
        "icon": "🔄",
        "category": "milestone",
        "points": 30
    },
    "ten_sessions": {
        "name": "수업 마스터 도전",
        "description": "10회의 마이크로티칭 세션을 완료했습니다",
        "icon": "🏆",
        "category": "milestone",
        "points": 50
    },
    "score_80": {
        "name": "우수 수업",
        "description": "80점 이상의 평가 점수를 달성했습니다",
        "icon": "⭐",
        "category": "achievement",
        "points": 25
    },
    "score_90": {
        "name": "탁월한 수업",
        "description": "90점 이상의 평가 점수를 달성했습니다",
        "icon": "🌟",
        "category": "achievement",
        "points": 50
    },
    "consistent_improvement": {
        "name": "꾸준한 성장",
        "description": "3회 연속 점수가 향상되었습니다",
        "icon": "📈",
        "category": "growth",
        "points": 40
    },
    "voice_master": {
        "name": "음성 전달 전문가",
        "description": "음성 전달 차원에서 만점을 달성했습니다",
        "icon": "🎤",
        "category": "skill",
        "points": 30
    },
    "interaction_master": {
        "name": "상호작용 전문가",
        "description": "교수학습 상호작용 차원에서 만점을 달성했습니다",
        "icon": "🤝",
        "category": "skill",
        "points": 30
    },
    "nonverbal_master": {
        "name": "비언어적 소통 전문가",
        "description": "비언어적 소통 차원에서 만점을 달성했습니다",
        "icon": "👐",
        "category": "skill",
        "points": 30
    }
}


class BadgeInfo(BaseModel):
    """배지 정보"""
    id: str
    name: str
    description: str
    icon: str
    category: str
    points: int


class StudentBadge(BaseModel):
    """학생 보유 배지"""
    badge_id: str
    name: str
    icon: str
    earned_at: str
    points: int


@router.get("/", response_model=List[BadgeInfo])
async def list_all_badges():
    """모든 배지 목록"""
    return [
        BadgeInfo(id=badge_id, **badge_data)
        for badge_id, badge_data in BADGE_DEFINITIONS.items()
    ]


@router.get("/{badge_id}", response_model=BadgeInfo)
async def get_badge_info(badge_id: str):
    """배지 상세 정보"""
    if badge_id not in BADGE_DEFINITIONS:
        raise HTTPException(status_code=404, detail="배지를 찾을 수 없습니다")
    
    return BadgeInfo(id=badge_id, **BADGE_DEFINITIONS[badge_id])


@router.get("/student/{student_id}")
async def get_student_badges(student_id: str):
    """학생 보유 배지 목록"""
    from app.api.portfolio import portfolio_store
    
    if student_id not in portfolio_store:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다")
    
    portfolio = portfolio_store[student_id]
    badges = portfolio.get("badges", [])
    
    earned_badges = []
    total_points = 0
    
    for badge_id in badges:
        if badge_id in BADGE_DEFINITIONS:
            badge_data = BADGE_DEFINITIONS[badge_id]
            earned_badges.append({
                "badge_id": badge_id,
                "name": badge_data["name"],
                "icon": badge_data["icon"],
                "category": badge_data["category"],
                "points": badge_data["points"],
                "earned_at": portfolio.get("updated_at", datetime.now().isoformat())
            })
            total_points += badge_data["points"]
    
    return {
        "student_id": student_id,
        "total_badges": len(earned_badges),
        "total_points": total_points,
        "badges": earned_badges
    }


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 10):
    """배지 포인트 리더보드"""
    from app.api.portfolio import portfolio_store
    
    leaderboard = []
    
    for student_id, portfolio in portfolio_store.items():
        badges = portfolio.get("badges", [])
        total_points = sum(
            BADGE_DEFINITIONS[b]["points"] 
            for b in badges 
            if b in BADGE_DEFINITIONS
        )
        
        leaderboard.append({
            "student_id": student_id,
            "name": portfolio["profile"]["name"],
            "total_badges": len(badges),
            "total_points": total_points
        })
    
    leaderboard.sort(key=lambda x: x["total_points"], reverse=True)
    
    return {
        "total_students": len(leaderboard),
        "leaderboard": leaderboard[:limit]
    }


@router.post("/verify/{badge_id}")
async def verify_badge(badge_id: str, student_id: str):
    """
    배지 인증서 발급 (디지털 배지 검증)
    """
    from app.api.portfolio import portfolio_store
    
    if student_id not in portfolio_store:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다")
    
    if badge_id not in BADGE_DEFINITIONS:
        raise HTTPException(status_code=404, detail="배지를 찾을 수 없습니다")
    
    portfolio = portfolio_store[student_id]
    
    if badge_id not in portfolio.get("badges", []):
        raise HTTPException(status_code=400, detail="학생이 해당 배지를 보유하고 있지 않습니다")
    
    badge_data = BADGE_DEFINITIONS[badge_id]
    
    # 디지털 배지 인증서 정보
    certificate = {
        "verified": True,
        "badge_id": badge_id,
        "badge_name": badge_data["name"],
        "issuer": "GINUE AI Microteaching Lab (GAIM Lab)",
        "recipient": {
            "student_id": student_id,
            "name": portfolio["profile"]["name"]
        },
        "issued_at": portfolio.get("updated_at", datetime.now().isoformat()),
        "verification_url": f"https://gaimlab.ginue.ac.kr/verify/{badge_id}/{student_id}"
    }
    
    return certificate
