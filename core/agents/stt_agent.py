"""
🗣️ STT Agent - 음성→텍스트 변환 전문 에이전트
v6.1: pyannote.audio 실제 화자 분리 + 휴리스틱 폴백
"""

import re
import os
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

try:
    # == 호환성 패치: pyannote 4.0.x의 내부 의존성이 사용하는 제거된 API 복원 ==
    # torchaudio 2.2+ 에서 제거된 backend API 스텁
    import torchaudio, sys as _sys, types
    if not hasattr(torchaudio, 'set_audio_backend'):
        torchaudio.set_audio_backend = lambda x: None
    if not hasattr(torchaudio, 'list_audio_backends'):
        torchaudio.list_audio_backends = lambda: ['soundfile']
    if not hasattr(torchaudio, 'get_audio_backend'):
        torchaudio.get_audio_backend = lambda: 'soundfile'
    # torchaudio.backend.common.AudioMetaData 모듈 mock (pyannote 내부 의존)
    if 'torchaudio.backend' not in _sys.modules:
        from collections import namedtuple
        _AudioMetaData = namedtuple('AudioMetaData', [
            'sample_rate', 'num_frames', 'num_channels', 'bits_per_sample', 'encoding'
        ], defaults=[0, 0, 0, 0, ''])
        _backend = types.ModuleType('torchaudio.backend')
        _backend_common = types.ModuleType('torchaudio.backend.common')
        _backend_common.AudioMetaData = _AudioMetaData
        _backend.common = _backend_common
        _sys.modules['torchaudio.backend'] = _backend
        _sys.modules['torchaudio.backend.common'] = _backend_common
    # torchaudio.info 스텁 (2.10에서 제거됨, speechbrain 내부 의존)
    if not hasattr(torchaudio, 'info'):
        def _torchaudio_info(path, **kwargs):
            import soundfile as _sf
            _i = _sf.info(str(path))
            from collections import namedtuple as _nt
            _AM = _nt('AudioMetaData', ['sample_rate','num_frames','num_channels','bits_per_sample','encoding'],
                       defaults=[0, 0, 0, 0, ''])
            return _AM(sample_rate=_i.samplerate, num_frames=_i.frames,
                       num_channels=_i.channels, bits_per_sample=_i.subtype_info.split()[0] if _i.subtype_info else 16,
                       encoding=_i.subtype or '')
        torchaudio.info = _torchaudio_info
    # numpy 2.0+에서 제거된 np.NaN, np.NAN 복원
    import numpy as _np
    if not hasattr(_np, 'NaN'):
        _np.NaN = _np.nan
    if not hasattr(_np, 'NAN'):
        _np.NAN = _np.nan
    # torchcodec DLL 로딩 실패 시 mock 모듈 주입 (Windows 호환)
    try:
        from torchcodec.decoders import AudioDecoder
    except Exception:
        import types, sys as _sys
        _tc = types.ModuleType('torchcodec')
        _tc_dec = types.ModuleType('torchcodec.decoders')
        class _MockAudioDecoder:
            def __init__(self, src): self._src = src
            @property
            def metadata(self):
                import soundfile as _sf
                info = _sf.info(self._src)
                class _M:
                    sample_rate = info.samplerate
                    num_channels = info.channels
                    num_frames = info.frames
                    duration_seconds_from_header = info.frames / info.samplerate
                return _M()
            def get_all_samples(self):
                import soundfile as _sf, torch
                data, sr = _sf.read(self._src, dtype='float32')
                if data.ndim == 1: data = data[None, :]
                else: data = data.T
                class _S:
                    pass
                s = _S(); s.data = torch.from_numpy(data); s.sample_rate = sr
                return s
            def get_samples_played_in_range(self, start, end):
                import soundfile as _sf, torch
                info = _sf.info(self._src)
                sr = info.samplerate
                start_f = int(start * sr); end_f = int(end * sr)
                data, _ = _sf.read(self._src, start=start_f, stop=end_f, dtype='float32')
                if data.ndim == 1: data = data[None, :]
                else: data = data.T
                class _S:
                    pass
                s = _S(); s.data = torch.from_numpy(data); s.sample_rate = sr
                return s
        class _MockAudioStreamMetadata:
            pass
        class _MockAudioSamples:
            pass
        _tc_dec.AudioDecoder = _MockAudioDecoder
        _tc_dec.AudioStreamMetadata = _MockAudioStreamMetadata
        _tc.AudioSamples = _MockAudioSamples
        _tc.decoders = _tc_dec
        _sys.modules['torchcodec'] = _tc
        _sys.modules['torchcodec.decoders'] = _tc_dec

    # huggingface_hub 1.x: use_auth_token → token 일괄 변환
    import huggingface_hub as _hfh
    import functools
    def _hf_compat_wrapper(orig_fn):
        @functools.wraps(orig_fn)
        def wrapper(*args, **kwargs):
            if 'use_auth_token' in kwargs:
                kwargs['token'] = kwargs.pop('use_auth_token')
            return orig_fn(*args, **kwargs)
        return wrapper
    for _fn_name in ['hf_hub_download', 'model_info', 'upload_file', 'create_repo']:
        if hasattr(_hfh, _fn_name):
            setattr(_hfh, _fn_name, _hf_compat_wrapper(getattr(_hfh, _fn_name)))
    # HfApi 메서드도 패치
    if hasattr(_hfh, 'HfApi'):
        for _m in ['model_info', 'hf_hub_download']:
            if hasattr(_hfh.HfApi, _m):
                setattr(_hfh.HfApi, _m, _hf_compat_wrapper(getattr(_hfh.HfApi, _m)))
    # torch.load 호환: pyannote 모델이 weights_only=True (PyTorch 2.10 기본값)에서 실패
    # torch.serialization.load 레벨에서 패치해야 pyannote 내부 호출도 적용됨
    import torch, torch.serialization
    _original_torch_ser_load = torch.serialization.load
    @functools.wraps(_original_torch_ser_load)
    def _compat_torch_load(*args, **kwargs):
        kwargs['weights_only'] = False
        return _original_torch_ser_load(*args, **kwargs)
    torch.serialization.load = _compat_torch_load
    torch.load = _compat_torch_load

    from pyannote.audio import Pipeline as PyannotePipeline
    # pyannote 내부 모듈의 로컬 참조 패치
    import pyannote.audio.core.pipeline as _pa_pipeline
    import pyannote.audio.core.model as _pa_model
    if hasattr(_pa_pipeline, 'hf_hub_download'):
        _pa_pipeline.hf_hub_download = _hf_compat_wrapper(_pa_pipeline.hf_hub_download)
    if hasattr(_pa_model, 'hf_hub_download'):
        _pa_model.hf_hub_download = _hf_compat_wrapper(_pa_model.hf_hub_download)
    # pyannote model 모듈의 torch.load도 패치
    _pa_model.torch.load = _compat_torch_load
    _pa_model.torch.serialization.load = _compat_torch_load
    HAS_PYANNOTE = True
except (ImportError, Exception) as _pyannote_err:
    HAS_PYANNOTE = False


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
    diarization_method: str = "none"    # v6.1: "pyannote" / "heuristic" / "none"

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
            "diarization_method": self.diarization_method,
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
    🗣️ STT Agent v6.1
    음성 데이터를 텍스트로 변환하고 언어 패턴을 분석합니다.

    v6.1 추가:
    - pyannote.audio 기반 실제 화자 분리 (DNN)
    - Whisper 세그먼트 ↔ pyannote 타임라인 IOU 매칭
    - 폴백: pyannote 실패 시 에너지/발화 휴리스틱
    """

    def __init__(self, model_size: str = "base", language: str = "ko"):
        self.model_size = model_size
        self.language = language
        self._whisper_model = None
        self._faster_model = None
        self._pyannote_pipeline = None

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

        # v6.1: 화자 분리 — pyannote 우선, 폴백 heuristic
        diarization_done = False
        if result.segments and HAS_PYANNOTE:
            try:
                self._pyannote_diarization(result, str(path))
                diarization_done = True
            except Exception as e:
                print(f"[STT Agent] pyannote 화자 분리 실패, 휴리스틱 폴백: {e}")

        if not diarization_done and result.segments and HAS_LIBROSA:
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
    # v6.1: pyannote.audio 실제 화자 분리
    # ================================================================

    def _pyannote_diarization(self, result: STTResult, audio_path: str):
        """
        pyannote.audio 기반 실제 화자 분리 (v6.1)

        Whisper 세그먼트와 pyannote 타임라인을 IOU 매칭하여
        각 발화에 화자를 할당한다.
        교사 = 가장 긴 발화 시간의 화자 (수업 실연에서 교사가 대부분 발화)
        """
        import torch

        hf_token = os.getenv("HF_TOKEN", "")
        if not hf_token:
            raise ValueError("HF_TOKEN 환경변수가 설정되지 않았습니다.")

        # 파이프라인 로드 (캐싱)
        if self._pyannote_pipeline is None:
            os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token
            os.environ["HF_TOKEN"] = hf_token
            self._pyannote_pipeline = PyannotePipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
            )

        # 화자 분리 실행 (화자 수 힌트: 교사 + 학생들)
        # torchcodec mock이 soundfile로 오디오를 읽어 pyannote에 전달
        diarization = self._pyannote_pipeline(audio_path, min_speakers=1, max_speakers=4)

        # pyannote 타임라인 수집
        pyannote_segments = []
        speaker_durations = {}  # 각 화자의 총 발화 시간
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            pyannote_segments.append({
                "start": segment.start,
                "end": segment.end,
                "speaker_id": speaker,
            })
            speaker_durations[speaker] = speaker_durations.get(speaker, 0) + (segment.end - segment.start)

        if not pyannote_segments:
            raise ValueError("pyannote 결과가 비어있습니다.")

        # 교사 = 가장 많이 발화한 화자
        teacher_id = max(speaker_durations, key=speaker_durations.get)

        # Whisper 세그먼트 ↔ pyannote IOU 매칭
        speaker_segs = []
        prev_speaker = None
        interaction_count = 0

        for seg in result.segments:
            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", 0)
            text = seg.get("text", "")

            # IOU 기반 화자 매칭
            best_speaker_id = teacher_id
            best_overlap = 0

            for ps in pyannote_segments:
                overlap_start = max(seg_start, ps["start"])
                overlap_end = min(seg_end, ps["end"])
                overlap = max(0, overlap_end - overlap_start)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker_id = ps["speaker_id"]

            speaker = "teacher" if best_speaker_id == teacher_id else "student"
            confidence = min(1.0, best_overlap / max(seg_end - seg_start, 0.01))

            if prev_speaker is not None and speaker != prev_speaker:
                interaction_count += 1
            prev_speaker = speaker

            speaker_segs.append({
                "start": seg_start,
                "end": seg_end,
                "speaker": speaker,
                "speaker_id": best_speaker_id,
                "text": text,
                "confidence": round(confidence, 2),
            })

        result.speaker_segments = speaker_segs
        result.interaction_count = interaction_count
        result.diarization_method = "pyannote"

        # 교사/학생 발화 비율
        teacher_time = sum(s["end"] - s["start"] for s in speaker_segs if s["speaker"] == "teacher")
        student_time = sum(s["end"] - s["start"] for s in speaker_segs if s["speaker"] == "student")
        total_time = teacher_time + student_time
        result.teacher_ratio = teacher_time / total_time if total_time > 0 else 0.75
        result.student_turns = sum(1 for s in speaker_segs if s["speaker"] == "student")

        print(f"[STT Agent] pyannote 화자 분리 완료: "
              f"{len(speaker_durations)}명 감지, 교사={teacher_id}, "
              f"교사비율={result.teacher_ratio:.1%}, 학생발화={result.student_turns}회")

    # ================================================================
    # v6.0: 휴리스틱 화자 분리 (폴백)
    # ================================================================

    def _simple_diarization(self, result: STTResult, audio_path: str):
        """
        에너지/발화 길이 기반 경량 화자 분리 (v6.0 개선)

        v6.0 개선:
        - 에너지 비율 변화 > 1.5배 → 화자 전환 후보
        - 교사 짧은 질문 오분류 방지 (질문 패턴 감지)
        - 화자 분류 confidence 필드 추가
        """
        try:
            y, sr = librosa.load(audio_path, sr=16000)
        except Exception:
            return

        speaker_segs = []
        prev_speaker = "teacher"
        prev_energy = 0.0
        interaction_count = 0

        # 교사 질문 패턴 (짧지만 학생이 아닌 경우)
        teacher_question_patterns = [
            "맞아", "맞죠", "그렇죠", "아니야", "이해했죠",
            "해볼까", "해보세요", "읽어봐", "발표해",
            "뭐예요", "누가", "어떤", "이건 뭐", "알검",
            "다같이", "함께", "여러분", "바로",
        ]

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

            # v6.0: 에너지 비율 변화 감지
            energy_ratio = energy / prev_energy if prev_energy > 0.001 else 1.0

            # v6.0: 교사 질문 패턴 검사 (짧지만 교사 발화인 경우)
            is_teacher_question = any(p in text for p in teacher_question_patterns)

            # 화자 판별 규칙 (v6.0 개선)
            confidence = 0.5  # 기본 확신도

            if seg_duration < 1.5 and len(text.split()) < 5 and not is_teacher_question:
                # 매우 짧은 응답 + 교사 질문 아님 → 학생
                speaker = "student"
                confidence = 0.7
            elif seg_duration < 2.5 and self._is_response_pattern(text) and not is_teacher_question:
                # 짧은 응답 패턴 → 학생
                speaker = "student"
                confidence = 0.65
            elif energy_ratio > 1.8 and seg_duration < 3.0 and not is_teacher_question:
                # v6.0: 에너지 급변 + 짧은 발화 → 화자 전환 (학생)
                speaker = "student"
                confidence = 0.55
            elif is_teacher_question:
                # 교사 질문 패턴 → 교사 (짧아도)
                speaker = "teacher"
                confidence = 0.8
            else:
                speaker = "teacher"
                confidence = 0.75

            # 교대 횟수 카운트
            if speaker != prev_speaker:
                interaction_count += 1
            prev_speaker = speaker
            prev_energy = energy

            speaker_segs.append({
                "start": start,
                "end": end,
                "speaker": speaker,
                "text": text,
                "energy": round(energy, 4),
                "confidence": round(confidence, 2),  # v6.0 추가
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
        result.diarization_method = "heuristic"

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
