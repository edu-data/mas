"""
📝 Text Analyzer - 강의 텍스트 분석 모듈
faster-whisper STT + '좋은 수업' 관점 텍스트 분석

분석 지표:
1. 교수 화법: 용어 설명, 예시 사용, 강조 표현
2. 학습자 참여: 질문 기법, 참여 유도
3. 구조화: 도입, 전환, 요약 표현
4. 평가 및 정리: 이해 점검, 마무리
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

# whisper 조건부 임포트 (openai-whisper)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("[!] openai-whisper not available. Run: pip install openai-whisper")


@dataclass
class TextSegment:
    """텍스트 세그먼트"""
    start: float
    end: float
    text: str


@dataclass
class TextAnalysisResult:
    """텍스트 분석 결과"""
    transcript: str                          # 전체 텍스트
    segments: List[TextSegment]              # 세그먼트별 텍스트
    teaching_metrics: Dict                   # 교수 화법 지표
    interaction_metrics: Dict                # 상호작용 지표
    structure_metrics: Dict                  # 구조화 지표
    quality_score: float                     # 종합 점수
    word_count: int                          # 총 단어 수
    duration_seconds: float                  # 분석된 오디오 길이


# =====================================================
# 1. STT (Speech-to-Text) - openai-whisper
# =====================================================
def transcribe_audio(
    audio_path: str,
    model_size: str = "small",
    language: str = "ko"
) -> Tuple[str, List[TextSegment]]:
    """
    오디오 파일을 텍스트로 변환 (openai-whisper)
    
    Args:
        audio_path: WAV/MP3 오디오 파일 경로
        model_size: 모델 크기 (tiny, base, small, medium, large)
        language: 언어 코드 (ko=한국어, en=영어)
        
    Returns:
        (전체 텍스트, 세그먼트 리스트)
    """
    if not WHISPER_AVAILABLE:
        print("[!] openai-whisper가 설치되지 않았습니다.")
        return "", []
    
    if not os.path.exists(audio_path):
        print(f"[!] 오디오 파일을 찾을 수 없습니다: {audio_path}")
        return "", []
    
    print(f"📝 [STT] Whisper 모델 로딩... ({model_size})")
    
    # 모델 로드
    model = whisper.load_model(model_size)
    
    print(f"   언어: {language}")
    print(f"   🎙️ 음성 인식 중...")
    
    # 음성 인식 실행
    result = model.transcribe(
        audio_path,
        language=language,
        verbose=False
    )
    
    segments = []
    for seg in result.get("segments", []):
        segment = TextSegment(
            start=seg["start"],
            end=seg["end"],
            text=seg["text"].strip()
        )
        segments.append(segment)
    
    full_text = result.get("text", "").strip()
    
    print(f"   ✅ STT 완료: {len(segments)}개 세그먼트, {len(full_text)}자")
    
    return full_text, segments


# =====================================================
# 2. 교수 화법 분석 (수업 전달)
# =====================================================
def analyze_teaching_speech(text: str) -> Dict:
    """
    교수 화법 분석
    
    분석 항목:
    - 용어 설명: "~란", "~이란", "~의 의미는" 등
    - 예시 사용: "예를 들어", "예컨대" 등
    - 강조 표현: "중요한", "핵심", "반드시" 등
    """
    # 용어 설명 패턴
    term_patterns = [
        r'[가-힣]+[이]?란',           # ~란, ~이란
        r'의\s*의미는',                # ~의 의미는
        r'[가-힣]+[을를]\s*말[합하]',  # ~를 말합니다
        r'정의[하해]',                 # 정의하면, 정의해보면
        r'뜻[은이]',                   # ~의 뜻은
    ]
    
    # 예시 사용 패턴
    example_patterns = [
        r'예를\s*들[어면]',            # 예를 들어, 예를 들면
        r'예컨대',
        r'[예사]례[로를]',             # 예로, 사례로
        r'예[시제]',                   # 예시, 예제
        r'가령',
        r'for\s*example',
        r'실[제례][로의]',             # 실제로, 실례로
    ]
    
    # 강조 표현 패턴
    emphasis_patterns = [
        r'중요[한합]',                 # 중요한, 중요합니다
        r'핵심[은적]?',                # 핵심, 핵심은, 핵심적
        r'반드시',
        r'꼭',
        r'필수[적]?',
        r'절대[로]?',
        r'특[히별]',                   # 특히, 특별히
        r'주[목의][하해]',             # 주목하세요, 주의하세요
    ]
    
    # 패턴 매칭 카운트
    term_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in term_patterns)
    example_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in example_patterns)
    emphasis_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in emphasis_patterns)
    
    # 단어 수 기준 정규화 (1000단어당 빈도)
    word_count = len(text.split())
    normalize = lambda x: (x / max(1, word_count)) * 1000
    
    return {
        "term_explanation_count": term_count,
        "term_explanation_per_1000": round(normalize(term_count), 2),
        "example_usage_count": example_count,
        "example_usage_per_1000": round(normalize(example_count), 2),
        "emphasis_count": emphasis_count,
        "emphasis_per_1000": round(normalize(emphasis_count), 2),
        "teaching_speech_score": min(100, (term_count * 5 + example_count * 8 + emphasis_count * 3))
    }


# =====================================================
# 3. 상호작용 분석 (학습자 참여)
# =====================================================
def analyze_interaction(text: str) -> Dict:
    """
    상호작용(학습자 참여 유도) 분석
    
    분석 항목:
    - 질문 기법: 의문문 사용
    - 참여 유도: "생각해보세요", "해볼까요" 등
    """
    # 질문 패턴
    question_patterns = [
        r'[가-힣]+[까요][\?]?',        # ~할까요?, ~일까요?
        r'[가-힣]+[나요][\?]?',        # ~하나요?, ~인가요?
        r'[가-힣]+[을까][\?]?',        # ~일까?, ~할까?
        r'왜[일요\s]',                 # 왜 ~
        r'어떻[게]',                   # 어떻게
        r'무엇[을이]',                 # 무엇을, 무엇이
        r'어[떤디]',                   # 어떤, 어디
        r'누[가구]',                   # 누가, 누구
        r'언제',
        r'\?',                         # 물음표
    ]
    
    # 참여 유도 패턴
    participation_patterns = [
        r'생각[해보]',                 # 생각해보세요
        r'해[봐볼][요까]',             # 해봐요, 해볼까요
        r'어떤가요',
        r'어떠[세신]',                 # 어떠세요, 어떠신가요
        r'떠올[려라]',                 # 떠올려보세요
        r'상상[해]',
        r'[함께같이]',                 # 함께, 같이
        r'직접',
        r'여러분[은이]?',
    ]
    
    question_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in question_patterns)
    participation_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in participation_patterns)
    
    word_count = len(text.split())
    normalize = lambda x: (x / max(1, word_count)) * 1000
    
    return {
        "question_count": question_count,
        "question_per_1000": round(normalize(question_count), 2),
        "participation_prompt_count": participation_count,
        "participation_per_1000": round(normalize(participation_count), 2),
        "interaction_score": min(100, (question_count * 3 + participation_count * 5))
    }


# =====================================================
# 4. 구조화 분석 (수업 설계)
# =====================================================
def analyze_structure(text: str) -> Dict:
    """
    수업 구조화 분석
    
    분석 항목:
    - 도입: 학습 목표, 오늘, 이번 시간
    - 전환: 다음으로, 이제, 그러면
    - 요약: 정리하면, 핵심은, 요약
    """
    # 도입 패턴
    intro_patterns = [
        r'오늘은?',
        r'이번\s*시간',
        r'학습\s*목표',
        r'목[표적]',
        r'시작[하해]',
        r'살펴[보볼]',
        r'알아[보볼]',
    ]
    
    # 전환 패턴
    transition_patterns = [
        r'다음[으로]?',
        r'이[제젠]',
        r'그[러래럼]면',
        r'그[리래]고',
        r'또[한]?',
        r'마찬가지로',
        r'한편',
        r'반[면대][에로]?',
    ]
    
    # 요약 패턴
    summary_patterns = [
        r'정리[하해]면',
        r'요약[하해]',
        r'핵심은?',
        r'결론[은적]?',
        r'마무리',
        r'종합[하해]',
        r'다시\s*말[해하]',
        r'간단히',
    ]
    
    intro_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in intro_patterns)
    transition_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in transition_patterns)
    summary_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in summary_patterns)
    
    word_count = len(text.split())
    normalize = lambda x: (x / max(1, word_count)) * 1000
    
    return {
        "intro_count": intro_count,
        "intro_per_1000": round(normalize(intro_count), 2),
        "transition_count": transition_count,
        "transition_per_1000": round(normalize(transition_count), 2),
        "summary_count": summary_count,
        "summary_per_1000": round(normalize(summary_count), 2),
        "structure_score": min(100, (intro_count * 3 + transition_count * 2 + summary_count * 5))
    }


# =====================================================
# 5. 종합 분석
# =====================================================
def analyze_text_track(
    audio_path: str,
    model_size: str = "small"
) -> Optional[TextAnalysisResult]:
    """
    강의 오디오의 텍스트 종합 분석
    
    Args:
        audio_path: WAV 오디오 파일 경로
        model_size: Whisper 모델 크기
        
    Returns:
        TextAnalysisResult 객체 (STT 실패 시 None)
    """
    if not WHISPER_AVAILABLE:
        print("[!] faster-whisper가 설치되지 않아 텍스트 분석을 건너뜁니다.")
        return None
    
    # STT 실행
    full_text, segments = transcribe_audio(audio_path, model_size=model_size)
    
    if not full_text:
        print("[!] 텍스트 변환 실패")
        return None
    
    # 분석 시간 계산
    duration = segments[-1].end if segments else 0
    
    # 개별 분석 수행
    teaching_metrics = analyze_teaching_speech(full_text)
    interaction_metrics = analyze_interaction(full_text)
    structure_metrics = analyze_structure(full_text)
    
    # 종합 점수 계산 (가중 평균)
    quality_score = (
        teaching_metrics["teaching_speech_score"] * 0.4 +
        interaction_metrics["interaction_score"] * 0.35 +
        structure_metrics["structure_score"] * 0.25
    )
    
    word_count = len(full_text.split())
    
    print(f"\n📊 텍스트 분석 결과:")
    print(f"   단어 수: {word_count}개")
    print(f"   교수 화법 점수: {teaching_metrics['teaching_speech_score']}/100")
    print(f"   상호작용 점수: {interaction_metrics['interaction_score']}/100")
    print(f"   구조화 점수: {structure_metrics['structure_score']}/100")
    print(f"   📝 종합 점수: {quality_score:.1f}/100")
    
    return TextAnalysisResult(
        transcript=full_text,
        segments=segments,
        teaching_metrics=teaching_metrics,
        interaction_metrics=interaction_metrics,
        structure_metrics=structure_metrics,
        quality_score=quality_score,
        word_count=word_count,
        duration_seconds=duration
    )


# =====================================================
# CLI 테스트
# =====================================================
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        audio_file = r"D:\data science\lecture_coach\output\녹화_2025_02_21_08_37_50_910_audio.wav"
    
    if os.path.exists(audio_file):
        result = analyze_text_track(audio_file, model_size="small")
        if result:
            print(f"\n전체 텍스트 (첫 500자):")
            print(result.transcript[:500])
    else:
        print(f"파일을 찾을 수 없습니다: {audio_file}")
