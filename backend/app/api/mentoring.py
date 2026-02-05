"""
GAIM Lab - 멘토 매칭 API 엔드포인트
AI 분석 결과 + 멘토 피드백 통합
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
import uuid

router = APIRouter()

# 인메모리 멘토 저장소
mentor_store: Dict[str, Dict] = {}
feedback_store: Dict[str, List[Dict]] = {}  # analysis_id -> feedbacks


class MentorProfile(BaseModel):
    """멘토 프로필"""
    mentor_id: str
    name: str
    department: str
    specialization: List[str]
    email: str
    available: bool = True


class MentorFeedback(BaseModel):
    """멘토 피드백"""
    analysis_id: str
    mentor_id: str
    dimension_feedbacks: Dict[str, str]  # dimension -> feedback
    overall_comment: str
    recommendations: List[str]
    rating: int  # 1-5


class MentorMatchRequest(BaseModel):
    """멘토 매칭 요청"""
    student_id: str
    analysis_id: str
    weak_dimensions: List[str]  # 개선이 필요한 차원
    preferred_time: Optional[str] = None


# 샘플 멘토 데이터 초기화
SAMPLE_MENTORS = [
    {
        "mentor_id": "mentor_001",
        "name": "김교수",
        "department": "초등교육과",
        "specialization": ["수업 설계", "수업 전달", "수업 마무리"],
        "email": "kim@ginue.ac.kr",
        "available": True
    },
    {
        "mentor_id": "mentor_002", 
        "name": "이교수",
        "department": "교육학과",
        "specialization": ["교수학습 상호작용", "비언어적 소통"],
        "email": "lee@ginue.ac.kr",
        "available": True
    },
    {
        "mentor_id": "mentor_003",
        "name": "박교수",
        "department": "국어교육과",
        "specialization": ["음성 전달", "수업 전달"],
        "email": "park@ginue.ac.kr",
        "available": True
    }
]

# 초기화
for mentor in SAMPLE_MENTORS:
    mentor_store[mentor["mentor_id"]] = mentor


@router.get("/mentors", response_model=List[MentorProfile])
async def list_mentors():
    """모든 멘토 목록 조회"""
    return [MentorProfile(**m) for m in mentor_store.values()]


@router.get("/mentors/{mentor_id}", response_model=MentorProfile)
async def get_mentor(mentor_id: str):
    """멘토 상세 정보"""
    if mentor_id not in mentor_store:
        raise HTTPException(status_code=404, detail="멘토를 찾을 수 없습니다")
    return MentorProfile(**mentor_store[mentor_id])


@router.post("/match")
async def match_mentor(request: MentorMatchRequest):
    """
    AI 기반 멘토 자동 매칭
    
    학생의 약점 차원에 맞는 전문 멘토를 추천합니다.
    """
    weak_dims = set(request.weak_dimensions)
    
    # 전문 분야가 겹치는 멘토 찾기
    matched_mentors = []
    for mentor in mentor_store.values():
        if not mentor["available"]:
            continue
            
        specialization = set(mentor["specialization"])
        overlap = weak_dims & specialization
        
        if overlap:
            matched_mentors.append({
                "mentor": mentor,
                "match_score": len(overlap) / len(weak_dims),
                "matched_dimensions": list(overlap)
            })
    
    # 매칭 점수로 정렬
    matched_mentors.sort(key=lambda x: x["match_score"], reverse=True)
    
    if not matched_mentors:
        return {
            "status": "no_match",
            "message": "적합한 멘토를 찾을 수 없습니다",
            "recommendations": []
        }
    
    # 최적 매칭 결과
    best_match = matched_mentors[0]
    
    return {
        "status": "matched",
        "analysis_id": request.analysis_id,
        "student_id": request.student_id,
        "matched_mentor": {
            "mentor_id": best_match["mentor"]["mentor_id"],
            "name": best_match["mentor"]["name"],
            "email": best_match["mentor"]["email"],
            "match_score": round(best_match["match_score"] * 100, 1),
            "matched_dimensions": best_match["matched_dimensions"]
        },
        "alternative_mentors": [
            {
                "mentor_id": m["mentor"]["mentor_id"],
                "name": m["mentor"]["name"],
                "match_score": round(m["match_score"] * 100, 1)
            }
            for m in matched_mentors[1:3]  # 상위 2명 대안
        ]
    }


@router.post("/feedback")
async def submit_mentor_feedback(feedback: MentorFeedback):
    """
    멘토 피드백 제출
    
    AI 분석 결과에 대한 멘토의 정성적 피드백 추가
    """
    if feedback.mentor_id not in mentor_store:
        raise HTTPException(status_code=404, detail="멘토를 찾을 수 없습니다")
    
    feedback_entry = {
        "feedback_id": str(uuid.uuid4()),
        "analysis_id": feedback.analysis_id,
        "mentor_id": feedback.mentor_id,
        "mentor_name": mentor_store[feedback.mentor_id]["name"],
        "dimension_feedbacks": feedback.dimension_feedbacks,
        "overall_comment": feedback.overall_comment,
        "recommendations": feedback.recommendations,
        "rating": feedback.rating,
        "submitted_at": datetime.now().isoformat()
    }
    
    if feedback.analysis_id not in feedback_store:
        feedback_store[feedback.analysis_id] = []
    
    feedback_store[feedback.analysis_id].append(feedback_entry)
    
    return {
        "status": "submitted",
        "feedback_id": feedback_entry["feedback_id"],
        "message": "멘토 피드백이 등록되었습니다"
    }


@router.get("/feedback/{analysis_id}")
async def get_feedbacks(analysis_id: str):
    """
    분석에 대한 모든 멘토 피드백 조회
    
    AI 분석 + 멘토 피드백을 통합하여 입체적 코칭 제공
    """
    feedbacks = feedback_store.get(analysis_id, [])
    
    return {
        "analysis_id": analysis_id,
        "total_feedbacks": len(feedbacks),
        "feedbacks": feedbacks
    }


@router.get("/integrated/{analysis_id}")
async def get_integrated_coaching(analysis_id: str):
    """
    AI + 멘토 통합 코칭 결과
    
    Human-in-the-loop: AI 정량 분석 + 멘토 정성 피드백 결합
    """
    from app.api.analysis import analysis_store
    
    # AI 분석 결과 가져오기
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail="분석을 찾을 수 없습니다")
    
    analysis = analysis_store[analysis_id]
    
    if analysis["status"] != "completed":
        raise HTTPException(status_code=400, detail="분석이 완료되지 않았습니다")
    
    ai_result = analysis["result"]["gaim_evaluation"]
    
    # 멘토 피드백 가져오기
    mentor_feedbacks = feedback_store.get(analysis_id, [])
    
    # 통합 결과 생성
    integrated_result = {
        "analysis_id": analysis_id,
        "video_name": analysis.get("video_name", ""),
        
        # AI 분석 결과
        "ai_analysis": {
            "total_score": ai_result["total_score"],
            "grade": ai_result["grade"],
            "dimensions": ai_result["dimensions"],
            "strengths": ai_result["strengths"],
            "improvements": ai_result["improvements"],
            "overall_feedback": ai_result["overall_feedback"]
        },
        
        # 멘토 피드백 요약
        "mentor_coaching": {
            "total_reviews": len(mentor_feedbacks),
            "average_rating": (
                sum(f["rating"] for f in mentor_feedbacks) / len(mentor_feedbacks)
                if mentor_feedbacks else 0
            ),
            "feedbacks": mentor_feedbacks
        },
        
        # 통합 권장사항
        "integrated_recommendations": _generate_integrated_recommendations(
            ai_result, mentor_feedbacks
        )
    }
    
    return integrated_result


def _generate_integrated_recommendations(ai_result: Dict, feedbacks: List[Dict]) -> List[str]:
    """AI 결과와 멘토 피드백을 종합한 권장사항 생성"""
    recommendations = []
    
    # AI 분석 기반 권장사항
    for improvement in ai_result.get("improvements", []):
        recommendations.append(f"[AI] {improvement}")
    
    # 멘토 피드백 기반 권장사항
    for feedback in feedbacks:
        for rec in feedback.get("recommendations", []):
            recommendations.append(f"[멘토: {feedback['mentor_name']}] {rec}")
    
    return recommendations
