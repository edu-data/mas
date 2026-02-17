"""
🗣️ STT Agent - 음성→텍스트 변환 전문 에이전트
Whisper/Faster-Whisper 기반 STT 및 폴백 분석 지원
"""

import re
import subprocess
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


# 한국어 교육학 필러 단어
KOREAN_FILLER_WORDS = [
    "음", "어", "이제", "그래서", "자", "네", "예",
    "그러니까", "뭐", "약간", "좀", "한번", "그냥"
]


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
    🗣️ STT Agent
    음성 데이터를 텍스트로 변환하고 언어 패턴을 분석합니다.

    지원 엔진:
    1. Faster-Whisper (최우선 - 3x 속도)
    2. OpenAI Whisper (폴백)
    3. FFprobe 기반 메타데이터 분석 (ML 미설치 환경)
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

        return result.to_dict()

    def analyze_from_video(self, video_path: str) -> Dict:
        """
        비디오에서 직접 오디오를 추출하여 분석

        Args:
            video_path: 비디오 파일 경로

        Returns:
            STT 분석 결과 딕셔너리
        """
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

        # 한국어 평균 발화 속도: ~120 WPM (추정)
        estimated_wpm = 125.0
        speaking_ratio = 0.75  # 일반적으로 수업 시간의 75%가 발화

        estimated_word_count = int(estimated_wpm * (duration / 60) * speaking_ratio)

        return STTResult(
            transcript="[폴백 모드: 실제 텍스트 변환 없음. Whisper 설치 필요]",
            word_count=estimated_word_count,
            speaking_rate=estimated_wpm,
            duration_seconds=duration,
            filler_words={},
            filler_ratio=0.03,  # 평균 추정
            language=self.language,
            confidence=0.40,
            method="fallback",
        )

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
