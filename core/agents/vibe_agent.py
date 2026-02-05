"""
🔊 Vibe Agent - 음성 프로소디(운율) 분석
librosa를 활용한 톤, 속도, 휴지기 분석 (내용이 아닌 소리의 파형 분석)
"""

import numpy as np
import librosa
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from pathlib import Path


@dataclass
class VibeMetrics:
    """음성 프로소디 분석 결과"""
    segment_start: float           # 세그먼트 시작 시간 (초)
    segment_end: float             # 세그먼트 종료 시간 (초)
    pitch_mean: float = 0.0        # 평균 피치 (Hz)
    pitch_std: float = 0.0         # 피치 표준편차 (다양성)
    energy_mean: float = 0.0       # 평균 에너지 (RMS)
    energy_std: float = 0.0        # 에너지 표준편차
    speaking_rate: float = 0.0     # 말하기 속도 추정
    silence_ratio: float = 0.0     # 침묵 비율
    is_monotone: bool = False      # 단조로움 여부
    energy_level: str = "normal"   # low, normal, high


class VibeAgent:
    """
    🔊 Vibe Agent
    목소리의 톤, 빠르기, 휴지기 등 음성 프로소디(운율) 분석
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {
            "sample_rate": 22050,
            "monotone_threshold": 15,
            "silence_db": 20,
            "ideal_silence_ratio": (0.1, 0.3),
            "segment_duration": 10.0  # 분석 세그먼트 길이 (초)
        }
        
        self.results: List[VibeMetrics] = []
        self.audio_data: Optional[np.ndarray] = None
        self.sr: int = self.config["sample_rate"]
    
    def load_audio(self, audio_path: Path) -> None:
        """오디오 파일 로드"""
        print(f"🔊 오디오 로드 중: {audio_path}")
        self.audio_data, self.sr = librosa.load(
            str(audio_path), 
            sr=self.config["sample_rate"]
        )
        print(f"✅ 로드 완료: {len(self.audio_data)/self.sr:.1f}초")
    
    def analyze_full(self, audio_path: Optional[Path] = None) -> List[VibeMetrics]:
        """
        전체 오디오 분석 (세그먼트 단위)
        
        Args:
            audio_path: 오디오 파일 경로 (None이면 이미 로드된 데이터 사용)
            
        Returns:
            VibeMetrics 리스트
        """
        if audio_path:
            self.load_audio(audio_path)
        
        if self.audio_data is None:
            raise ValueError("오디오가 로드되지 않았습니다")
        
        duration = len(self.audio_data) / self.sr
        segment_duration = self.config["segment_duration"]
        
        print(f"📊 프로소디 분석 시작 (총 {duration:.1f}초, 세그먼트: {segment_duration}초)")
        
        self.results = []
        current_time = 0
        
        while current_time < duration:
            end_time = min(current_time + segment_duration, duration)
            metrics = self.analyze_segment(current_time, end_time)
            self.results.append(metrics)
            current_time = end_time
        
        print(f"✅ 프로소디 분석 완료: {len(self.results)}개 세그먼트")
        return self.results
    
    def analyze_segment(self, start_time: float, end_time: float) -> VibeMetrics:
        """
        특정 구간의 음성 프로소디 분석
        
        Args:
            start_time: 시작 시간 (초)
            end_time: 종료 시간 (초)
            
        Returns:
            VibeMetrics 객체
        """
        # 세그먼트 추출
        start_sample = int(start_time * self.sr)
        end_sample = int(end_time * self.sr)
        segment = self.audio_data[start_sample:end_sample]
        
        if len(segment) == 0:
            return VibeMetrics(segment_start=start_time, segment_end=end_time)
        
        metrics = VibeMetrics(segment_start=start_time, segment_end=end_time)
        
        # 1. 피치 분석
        self._analyze_pitch(segment, metrics)
        
        # 2. 에너지 분석
        self._analyze_energy(segment, metrics)
        
        # 3. 침묵 분석
        self._analyze_silence(segment, metrics)
        
        # 4. 단조로움 판정
        self._check_monotone(metrics)
        
        return metrics
    
    def _analyze_pitch(self, segment: np.ndarray, metrics: VibeMetrics):
        """피치(음높이) 분석"""
        # librosa의 piptrack으로 피치 추출
        pitches, magnitudes = librosa.piptrack(
            y=segment, 
            sr=self.sr,
            fmin=50,   # 최소 주파수 (일반 음성)
            fmax=500   # 최대 주파수
        )
        
        # 유효한 피치만 추출
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        if pitch_values:
            metrics.pitch_mean = np.mean(pitch_values)
            metrics.pitch_std = np.std(pitch_values)
    
    def _analyze_energy(self, segment: np.ndarray, metrics: VibeMetrics):
        """에너지(음량) 분석"""
        # RMS 에너지 계산
        rms = librosa.feature.rms(y=segment)[0]
        
        metrics.energy_mean = float(np.mean(rms))
        metrics.energy_std = float(np.std(rms))
        
        # 에너지 레벨 분류
        if metrics.energy_mean < 0.02:
            metrics.energy_level = "low"
        elif metrics.energy_mean > 0.1:
            metrics.energy_level = "high"
        else:
            metrics.energy_level = "normal"
    
    def _analyze_silence(self, segment: np.ndarray, metrics: VibeMetrics):
        """침묵(휴지기) 분석"""
        # 비침묵 구간 탐지
        intervals = librosa.effects.split(
            segment, 
            top_db=self.config["silence_db"]
        )
        
        # 말하는 구간의 총 길이
        speaking_samples = sum(end - start for start, end in intervals)
        total_samples = len(segment)
        
        metrics.silence_ratio = 1 - (speaking_samples / total_samples)
        
        # 말하기 속도 추정 (비침묵 구간 당 평균 길이)
        if len(intervals) > 0:
            avg_speaking_duration = speaking_samples / len(intervals) / self.sr
            metrics.speaking_rate = 1 / avg_speaking_duration if avg_speaking_duration > 0 else 0
    
    def _check_monotone(self, metrics: VibeMetrics):
        """단조로움 판정"""
        threshold = self.config["monotone_threshold"]
        
        # 피치 표준편차가 낮으면 단조로움
        if metrics.pitch_std < threshold:
            metrics.is_monotone = True
        
        # 에너지 변화도 고려
        if metrics.energy_std < 0.01:
            metrics.is_monotone = True
    
    def get_summary(self) -> Dict:
        """분석 결과 요약"""
        if not self.results:
            return {"error": "분석 결과가 없습니다"}
        
        total = len(self.results)
        
        return {
            "total_segments": total,
            "avg_pitch": np.mean([r.pitch_mean for r in self.results if r.pitch_mean > 0]),
            "pitch_variety": np.mean([r.pitch_std for r in self.results]),
            "avg_energy": np.mean([r.energy_mean for r in self.results]),
            "energy_variety": np.mean([r.energy_std for r in self.results]),
            "avg_silence_ratio": np.mean([r.silence_ratio for r in self.results]),
            "monotone_ratio": sum(1 for r in self.results if r.is_monotone) / total,
            "energy_distribution": self._get_energy_distribution(),
            "warnings": self._get_warnings()
        }
    
    def _get_energy_distribution(self) -> Dict[str, float]:
        """에너지 레벨 분포"""
        if not self.results:
            return {}
        
        levels = [r.energy_level for r in self.results]
        total = len(levels)
        
        return {
            "low": levels.count("low") / total,
            "normal": levels.count("normal") / total,
            "high": levels.count("high") / total
        }
    
    def _get_warnings(self) -> List[str]:
        """경고 메시지 생성"""
        if not self.results:
            return []
        
        warnings = []
        ideal_min, ideal_max = self.config["ideal_silence_ratio"]
        
        # Calculate values directly to avoid recursion
        total = len(self.results)
        monotone_ratio = sum(1 for r in self.results if r.is_monotone) / total
        avg_silence_ratio = np.mean([r.silence_ratio for r in self.results])
        
        if monotone_ratio > 0.5:
            warnings.append("[!] Over 50% of segments have monotone tone")
        
        if avg_silence_ratio > ideal_max:
            warnings.append("[!] High silence ratio (hesitation or lack of preparation)")
        elif avg_silence_ratio < ideal_min:
            warnings.append("[!] Speaking too fast without pauses")
        
        return warnings
    
    def get_timeline(self) -> List[Dict]:
        """시간별 분석 결과"""
        return [
            {
                "start": r.segment_start,
                "end": r.segment_end,
                "pitch_std": r.pitch_std,
                "energy_mean": r.energy_mean,
                "silence_ratio": r.silence_ratio,
                "is_monotone": r.is_monotone
            }
            for r in self.results
        ]
    
    def find_monotone_segments(self) -> List[Tuple[float, float]]:
        """단조로운 구간 찾기"""
        return [
            (r.segment_start, r.segment_end)
            for r in self.results
            if r.is_monotone
        ]
    
    def reset(self):
        """분석 결과 초기화"""
        self.results = []
        self.audio_data = None
