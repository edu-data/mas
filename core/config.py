"""
멀티모달 렉처 코치 - 설정 파일
Multimodal Lecture Coach Configuration
"""

from pathlib import Path

# ============================================================
# 경로 설정
# ============================================================
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
REPORTS_DIR = BASE_DIR / "reports"
TEMPLATES_DIR = REPORTS_DIR / "templates"

# 테스트 영상 경로
SAMPLE_VIDEO = Path(r"D:\data science\02.21\녹화_2025_02_21_09_45_12_933.mp4")

# ============================================================
# Vision Agent 설정
# ============================================================
VISION_CONFIG = {
    "frame_sample_rate": 1.0,        # 초당 샘플링할 프레임 수
    "gesture_threshold": 0.6,         # 손 위치 활성화 임계값 (y좌표)
    "face_confidence": 0.5,           # 얼굴 인식 최소 신뢰도
}

# ============================================================
# Vibe Agent 설정 (Audio Analysis)
# ============================================================
VIBE_CONFIG = {
    "whisper_model": "base",          # tiny, base, small, medium, large
    "sample_rate": 22050,             # librosa 샘플링 레이트
    "segment_duration": 10.0,         # 분석 세그먼트 길이 (초)
    "monotone_threshold": 15,         # pitch_std < 이 값이면 단조로움
    "silence_db": 20,                 # 침묵 감지 데시벨 임계값
    "ideal_silence_ratio": (0.1, 0.3) # 이상적인 침묵 비율 범위
}

# ============================================================
# Content Agent 설정 (Slide Analysis - Local)
# ============================================================
CONTENT_CONFIG = {
    "text_density_threshold": 150,    # 글자 수 초과 시 경고
    "min_font_detection": 12,         # 최소 감지 폰트 크기
    "ocr_language": "kor+eng",        # Tesseract 언어
}

# ============================================================
# Master Agent 설정
# ============================================================
MASTER_CONFIG = {
    "segment_duration": 10.0,             # 분석 세그먼트 길이 (초)
    "death_valley_duration": 30,          # 연속 지루함 구간 최소 초
    "incongruence_threshold": 0.5,        # 불일치 감지 임계값
}

# ============================================================
# 135점 평가 프레임워크 매핑
# ============================================================
EVALUATION_FRAMEWORK = {
    "수업_설계": {
        "max_score": 30,
        "items": ["학습목표_명확성", "내용_구조화"]
    },
    "수업_전달": {
        "max_score": 45,
        "items": ["교수_화법", "시청각_자료", "시간_관리"]
    },
    "학습자_참여": {
        "max_score": 30,
        "items": ["상호작용", "동기_유발"]
    },
    "평가_및_정리": {
        "max_score": 30,
        "items": ["형성평가", "수업_마무리"]
    }
}
