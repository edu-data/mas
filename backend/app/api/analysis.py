"""
GAIM Lab - 분석 API 엔드포인트
영상 업로드, 분석 실행, 결과 조회
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
import uuid
import shutil
import json

from app.core.analyzer import GAIMAnalysisPipeline
from app.core.evaluator import GAIMLectureEvaluator

router = APIRouter()

# 인메모리 분석 상태 저장소 (프로덕션에서는 Redis/DB 사용)
analysis_store: Dict[str, Dict] = {}

# 디렉토리 설정
UPLOAD_DIR = Path("D:/AI/GAIM_Lab/uploads")
OUTPUT_DIR = Path("D:/AI/GAIM_Lab/output")


class AnalysisRequest(BaseModel):
    """분석 요청 모델"""
    use_turbo: bool = True
    use_text: bool = True


class AnalysisStatus(BaseModel):
    """분석 상태 응답 모델"""
    id: str
    status: str  # pending, processing, completed, failed
    progress: int
    message: str
    created_at: str
    completed_at: Optional[str] = None
    result_url: Optional[str] = None


class EvaluationResponse(BaseModel):
    """평가 결과 응답 모델"""
    id: str
    video_name: str
    total_score: float
    grade: str
    dimensions: List[Dict]
    strengths: List[str]
    improvements: List[str]
    overall_feedback: str


@router.post("/upload", response_model=AnalysisStatus)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    use_turbo: bool = True,
    use_text: bool = True
):
    """
    영상 업로드 및 분석 시작
    
    - **file**: 분석할 영상 파일 (MP4, AVI, MOV)
    - **use_turbo**: Turbo 모드 사용 여부 (기본: True)
    - **use_text**: 텍스트 분석 사용 여부 (기본: True)
    """
    # 파일 확장자 검증
    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"지원하지 않는 파일 형식입니다. 허용: {allowed_extensions}"
        )
    
    # 분석 ID 생성
    analysis_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 파일 저장
    save_path = UPLOAD_DIR / f"{analysis_id}_{timestamp}{file_ext}"
    
    try:
        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")
    
    # 분석 상태 초기화
    analysis_store[analysis_id] = {
        "id": analysis_id,
        "status": "pending",
        "progress": 0,
        "message": "분석 대기 중",
        "video_path": str(save_path),
        "video_name": file.filename,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "use_turbo": use_turbo,
        "use_text": use_text,
        "result": None
    }
    
    # 백그라운드 분석 시작
    background_tasks.add_task(run_analysis, analysis_id)
    
    return AnalysisStatus(
        id=analysis_id,
        status="pending",
        progress=0,
        message="분석이 시작되었습니다",
        created_at=analysis_store[analysis_id]["created_at"]
    )


async def run_analysis(analysis_id: str):
    """백그라운드 분석 실행"""
    if analysis_id not in analysis_store:
        return
    
    store = analysis_store[analysis_id]
    store["status"] = "processing"
    store["progress"] = 10
    store["message"] = "영상 분석 중..."
    
    try:
        # 분석 파이프라인 실행
        pipeline = GAIMAnalysisPipeline(
            use_turbo=store["use_turbo"],
            use_text=store["use_text"]
        )
        
        store["progress"] = 30
        store["message"] = "AI 분석 진행 중..."
        
        video_path = Path(store["video_path"])
        output_dir = OUTPUT_DIR / analysis_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 분석 수행
        result = await pipeline.analyze_video(video_path, output_dir)
        
        store["progress"] = 90
        store["message"] = "결과 생성 중..."
        
        # 결과 저장
        result_path = output_dir / "result.json"
        with result_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        store["status"] = "completed"
        store["progress"] = 100
        store["message"] = "분석 완료"
        store["completed_at"] = datetime.now().isoformat()
        store["result"] = result
        store["result_url"] = f"/output/{analysis_id}/result.json"
        
    except Exception as e:
        store["status"] = "failed"
        store["message"] = f"분석 실패: {str(e)}"
        store["progress"] = 0


@router.get("/{analysis_id}", response_model=AnalysisStatus)
async def get_analysis_status(analysis_id: str):
    """분석 상태 조회"""
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail="분석을 찾을 수 없습니다")
    
    store = analysis_store[analysis_id]
    
    return AnalysisStatus(
        id=store["id"],
        status=store["status"],
        progress=store["progress"],
        message=store["message"],
        created_at=store["created_at"],
        completed_at=store.get("completed_at"),
        result_url=store.get("result_url")
    )


@router.get("/{analysis_id}/result", response_model=EvaluationResponse)
async def get_analysis_result(analysis_id: str):
    """분석 결과 조회"""
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail="분석을 찾을 수 없습니다")
    
    store = analysis_store[analysis_id]
    
    if store["status"] != "completed":
        raise HTTPException(status_code=400, detail="분석이 아직 완료되지 않았습니다")
    
    result = store["result"]
    evaluation = result["gaim_evaluation"]
    
    return EvaluationResponse(
        id=analysis_id,
        video_name=store["video_name"],
        total_score=evaluation["total_score"],
        grade=evaluation["grade"],
        dimensions=evaluation["dimensions"],
        strengths=evaluation["strengths"],
        improvements=evaluation["improvements"],
        overall_feedback=evaluation["overall_feedback"]
    )


@router.get("/{analysis_id}/report")
async def download_report(analysis_id: str, format: str = "json"):
    """
    분석 리포트 다운로드
    
    - **format**: 리포트 형식 (json, pdf)
    """
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail="분석을 찾을 수 없습니다")
    
    store = analysis_store[analysis_id]
    
    if store["status"] != "completed":
        raise HTTPException(status_code=400, detail="분석이 아직 완료되지 않았습니다")
    
    output_dir = OUTPUT_DIR / analysis_id
    
    if format == "json":
        result_path = output_dir / "result.json"
        if result_path.exists():
            return FileResponse(
                path=str(result_path),
                filename=f"gaim_result_{analysis_id}.json",
                media_type="application/json"
            )
    elif format == "pdf":
        # PDF 리포트 생성 로직 (추후 구현)
        raise HTTPException(status_code=501, detail="PDF 리포트는 준비 중입니다")
    
    raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다")


@router.get("/")
async def list_analyses(limit: int = 10, offset: int = 0):
    """최근 분석 목록 조회"""
    analyses = list(analysis_store.values())
    analyses.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "total": len(analyses),
        "limit": limit,
        "offset": offset,
        "items": analyses[offset:offset + limit]
    }


@router.post("/demo")
async def run_demo_analysis():
    """
    데모 분석 실행 (더미 데이터)
    MLC 없이도 7차원 평가 결과를 확인 가능
    """
    from app.core.analyzer import GAIMAnalysisPipeline
    
    analysis_id = f"demo_{uuid.uuid4().hex[:8]}"
    
    pipeline = GAIMAnalysisPipeline()
    dummy_data = pipeline._get_dummy_analysis()
    evaluation = pipeline.evaluator.evaluate(dummy_data)
    
    result = {
        "id": analysis_id,
        "type": "demo",
        "video_name": "demo_lecture.mp4",
        "gaim_evaluation": pipeline.evaluator.to_dict(evaluation)
    }
    
    return result
