"""
🗣️ STT Agent - 음성→텍스트 변환 전문 에이전트
v5.0: 화자 분리(Speaker Diarization) + 상호작용 분석 추가
"""

import re
import subprocess
import numpy as np
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field


# 선택적 의존성
try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False


# 한국어 교육학 필러 단어
KOREAN_FILLER_WORDS = [
    "음", "어", "이제", "그래서", "자", "네", "예",
    "그러니까", "뭐", "약간", "좀", "한번", "그냥"
]


@dataclass
class SpeakerSegment:
    """화자별 발화 구간"""
    start: float
    end: float
    speaker: str           # "teacher" or "student"
    text: str = ""
    energy: float = 0.0


@dataclass
class STTResult:
    """STT 분석 결과"""
    transcript: str = ""
    word_count: int = 0
    speaking_rate: float = 0.0        # WPM (Words Per Minute)
    duration_seconds: float = 0.0
    filler_words: Dict[str, int] = field(default_factory=dict)
    filler_ratio: float = 0.0
    language: str = "ko"
    segments: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    method: str = "fallback"           # whisper / faster_whisper / fallback
    # v5.0 화자 분리 필드
    speaker_segments: List[Dict] = field(default_factory=list)
    teacher_ratio: float = 0.75
    student_turns: int = 0
    interaction_count: int = 0          # 교사↔학생 교대 횟수
    question_count: int = 0             # 질문 횟수 (문장부호 기반)

    def to_dict(self) -> Dict:
        return {
            "transcript": self.transcript[:500] if self.transcript else "",
            "transcript_length": len(self.transcript),
            "word_count": self.word_count,
            "speaking_rate": round(self.speaking_rate, 1),
            "speaking_pattern": self._classify_speaking_pattern(),
            "duration_seconds": round(self.duration_seconds, 1),
            "filler_words": self.filler_words,
            "filler_ratio": round(self.filler_ratio, 3),
            "filler_count": sum(self.filler_words.values()),
            "language": self.language,
            "segment_count": len(self.segments),
            "confidence": round(self.confidence, 2),
            "method": self.method,
            # v5.0
            "teacher_ratio": round(self.teacher_ratio, 3),
            "student_turns": self.student_turns,
            "interaction_count": self.interaction_count,
            "question_count": self.question_count,
            "speaker_segment_count": len(self.speaker_segments),
        }

    def _classify_speaking_pattern(self) -> str:
        """말하기 패턴 분류"""
        if self.speaking_rate < 80:
            return "느림 (Slow)"
        elif self.speaking_rate < 120:
            return "대화형 (Conversational)"
        elif self.speaking_rate < 160:
            return "강의형 (Lecture)"
        else:
            return "빠름 (Fast)"


class STTAgent:
    """
    🗣️ STT Agent v5.0
    음성 데이터를 텍스트로 변환하고 언어 패턴을 분석합니다.

    v5.0 추가:
    - 에너지/발화길이 기반 화자 분리 (경량)
    - 질문 횟수 감지
    - 교사-학생 교대 횟수 측정
    """

    def __init__(self, model_size: str = "base", language: str = "ko"):
        self.model_size = model_size
        self.language = language
        self._whisper_model = None
        self._faster_model = None

    def analyze(self, audio_path: str) -> Dict:
        """
        오디오 파일 분석

        Args:
            audio_path: WAV/MP3 오디오 파일 경로

        Returns:
            STT 분석 결과 딕셔너리
        """
        path = Path(audio_path)
        if not path.exists():
            return STTResult(method="error").to_dict()

        duration = self._get_audio_duration(str(path))

        # 엔진 우선순위: Faster-Whisper > Whisper > Fallback
        if HAS_FASTER_WHISPER:
            result = self._analyze_faster_whisper(str(path), duration)
        elif HAS_WHISPER:
            result = self._analyze_whisper(str(path), duration)
        else:
            result = self._analyze_fallback(str(path), duration)

        # v5.0: 화자 분리 + 질문 감지
        if result.segments and HAS_LIBROSA:
            self._simple_diarization(result, str(path))
        self._detect_questions(result)

        return result.to_dict()

    def analyze_from_video(self, video_path: str) -> Dict:
        """비디오에서 직접 오디오를 추출하여 분석"""
        import tempfile
        import os

        temp_audio = os.path.join(tempfile.gettempdir(), "gaim_stt_temp.wav")

        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                temp_audio
            ], capture_output=True, timeout=120)

            if Path(temp_audio).exists():
                return self.analyze(temp_audio)
        except Exception:
            pass

        # FFprobe 폴백
        duration = self._get_video_duration(video_path)
        return self._analyze_fallback(video_path, duration).to_dict()

    def _analyze_faster_whisper(self, audio_path: str, duration: float) -> STTResult:
        """Faster-Whisper 엔진으로 STT 수행"""
        try:
            if self._faster_model is None:
                self._faster_model = WhisperModel(
                    self.model_size, device="cpu", compute_type="int8"
                )

            segments, info = self._faster_model.transcribe(
                audio_path, language=self.language, beam_size=5
            )

            all_text = []
            seg_list = []
            for seg in segments:
                all_text.append(seg.text)
                seg_list.append({
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip(),
                })

            transcript = " ".join(all_text)
            word_count = len(transcript.split())

            result = STTResult(
                transcript=transcript,
                word_count=word_count,
                speaking_rate=round(word_count / (duration / 60), 1) if duration > 0 else 0,
                duration_seconds=duration,
                language=self.language,
                segments=seg_list,
                confidence=0.85,
                method="faster_whisper",
            )
            self._detect_fillers(result)
            return result

        except Exception as e:
            print(f"[STT Agent] Faster-Whisper 오류: {e}")
            return self._analyze_fallback(audio_path, duration)

    def _analyze_whisper(self, audio_path: str, duration: float) -> STTResult:
        """OpenAI Whisper 엔진으로 STT 수행"""
        try:
            if self._whisper_model is None:
                self._whisper_model = whisper.load_model(self.model_size)

            result = self._whisper_model.transcribe(
                audio_path, language=self.language
            )

            transcript = result.get("text", "")
            word_count = len(transcript.split())
            segments = [
                {
                    "start": round(s["start"], 2),
                    "end": round(s["end"], 2),
                    "text": s["text"].strip(),
                }
                for s in result.get("segments", [])
            ]

            stt_result = STTResult(
                transcript=transcript,
                word_count=word_count,
                speaking_rate=round(word_count / (duration / 60), 1) if duration > 0 else 0,
                duration_seconds=duration,
                language=self.language,
                segments=segments,
                confidence=0.80,
                method="whisper",
            )
            self._detect_fillers(stt_result)
            return stt_result

        except Exception as e:
            print(f"[STT Agent] Whisper 오류: {e}")
            return self._analyze_fallback(audio_path, duration)

    def _analyze_fallback(self, file_path: str, duration: float) -> STTResult:
        """ML 없이 FFprobe 메타데이터 기반 추정 분석"""
        if duration <= 0:
            duration = self._get_audio_duration(file_path) or 600.0

        estimated_wpm = 125.0
        speaking_ratio = 0.75
        estimated_word_count = int(estimated_wpm * (duration / 60) * speaking_ratio)

        return STTResult(
            transcript="[폴백 모드: 실제 텍스트 변환 없음. Whisper 설치 필요]",
            word_count=estimated_word_count,
            speaking_rate=estimated_wpm,
            duration_seconds=duration,
            filler_words={},
            filler_ratio=0.03,
            language=self.language,
            confidence=0.40,
            method="fallback",
        )

    # ================================================================
    # v5.0: 화자 분리 (Speaker Diarization)
    # ================================================================

    def _simple_diarization(self, result: STTResult, audio_path: str):
        """
        에너지/발화 길이 기반 경량 화자 분리

        원리: 교사는 주로 긴 발화(설명), 학생은 짧은 응답
        - 긴 세그먼트 (>3초) → 교사 발화
        - 짧은 세그먼트 (<2초) + 앞 세그먼트와 에너지 차이 → 학생 발화
        """
        try:
            y, sr = librosa.load(audio_path, sr=16000)
        except Exception:
            return

        speaker_segs = []
        prev_speaker = "teacher"
        interaction_count = 0

        for seg in result.segments:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "")
            seg_duration = end - start

            # 에너지 계산
            start_sample = int(start * sr)
            end_sample = min(int(end * sr), len(y))
            if end_sample <= start_sample:
                continue
            segment_audio = y[start_sample:end_sample]
            energy = float(np.sqrt(np.mean(segment_audio ** 2)))

            # 화자 판별 규칙
            if seg_duration < 1.5 and len(text.split()) < 5:
                # 매우 짧은 응답 → 학생 (높은 확률)
                speaker = "student"
            elif seg_duration < 2.5 and self._is_response_pattern(text):
                # 짧은 응답 패턴 → 학생
                speaker = "student"
            else:
                speaker = "teacher"

            # 교대 횟수 카운트
            if speaker != prev_speaker:
                interaction_count += 1
            prev_speaker = speaker

            speaker_segs.append({
                "start": start,
                "end": end,
                "speaker": speaker,
                "text": text,
                "energy": round(energy, 4),
            })

        result.speaker_segments = speaker_segs
        result.interaction_count = interaction_count

        # 교사/학생 발화 비율
        teacher_time = sum(
            s["end"] - s["start"] for s in speaker_segs if s["speaker"] == "teacher"
        )
        student_time = sum(
            s["end"] - s["start"] for s in speaker_segs if s["speaker"] == "student"
        )
        total_time = teacher_time + student_time
        result.teacher_ratio = teacher_time / total_time if total_time > 0 else 0.75
        result.student_turns = sum(1 for s in speaker_segs if s["speaker"] == "student")

    def _is_response_pattern(self, text: str) -> bool:
        """학생 응답 패턴 감지"""
        response_patterns = [
            "네", "예", "아", "맞아요", "알겠습니다", "감사합니다",
            "선생님", "저요", "여기요", "다섯", "하나", "둘", "셋", "넷",
        ]
        text_stripped = text.strip()
        for pat in response_patterns:
            if text_stripped == pat or text_stripped.startswith(pat + " "):
                return True
        return len(text_stripped) < 10

    # ================================================================
    # v5.0: 질문 감지
    # ================================================================

    def _detect_questions(self, result: STTResult):
        """발화에서 질문 횟수 감지"""
        if not result.transcript:
            return

        # 물음표 기반
        q_mark_count = result.transcript.count("?")

        # 한국어 질문 패턴 (? 없는 경우도 감지)
        question_patterns = [
            r'[가-힣]+\s*(?:할까요|할래요|할게요|해볼까)',
            r'[가-힣]+\s*(?:일까요|인가요|나요|까요|ㄹ까)',
            r'뭐가|어떤|왜|어떻게|몇\s*(?:개|명|번)',
            r'알겠[지죠]|이해[했하]|맞[지죠나]',
        ]

        pattern_count = 0
        for pat in question_patterns:
            pattern_count += len(re.findall(pat, result.transcript))

        result.question_count = max(q_mark_count, pattern_count)

    # ================================================================
    # 기존 유틸리티
    # ================================================================

    def _detect_fillers(self, result: STTResult):
        """한국어 필러 단어 감지"""
        if not result.transcript:
            return

        text = result.transcript
        filler_counts = {}
        total_fillers = 0

        for filler in KOREAN_FILLER_WORDS:
            count = len(re.findall(rf'\b{re.escape(filler)}\b', text))
            if count > 0:
                filler_counts[filler] = count
                total_fillers += count

        result.filler_words = filler_counts
        if result.word_count > 0:
            result.filler_ratio = total_fillers / result.word_count

    def _get_audio_duration(self, path: str) -> float:
        """FFprobe로 오디오 길이 조회"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-show_entries",
                "format=duration", "-of", "csv=p=0", path
            ]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(out.stdout.strip())
        except Exception:
            return 0.0

    def _get_video_duration(self, path: str) -> float:
        """FFprobe로 비디오 길이 조회"""
        return self._get_audio_duration(path)
