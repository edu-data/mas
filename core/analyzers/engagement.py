"""
📈 Engagement Analyzer - 몰입도 분석 및 히트맵 생성
시간별 몰입도를 계산하고 시각화
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import timedelta


@dataclass
class EngagementSegment:
    """몰입도 세그먼트"""
    start_time: float
    end_time: float
    score: float           # 0-100
    level: str             # low, normal, high
    factors: Dict[str, float]  # 점수에 기여한 요인들


class EngagementAnalyzer:
    """
    몰입도 분석기
    
    몰입도 계산 요소:
    - 제스처 활성화
    - 음성 다양성 (비단조로움)
    - 시선 접촉
    - 콘텐츠 복잡도 (적절할수록 좋음)
    """
    
    FACTOR_WEIGHTS = {
        "gesture": 0.30,      # 제스처
        "voice_variety": 0.25, # 음성 다양성
        "eye_contact": 0.20,   # 시선 접촉
        "content_clarity": 0.15, # 콘텐츠 명확성
        "expression": 0.10     # 표정 활력
    }
    
    LEVEL_THRESHOLDS = {
        "high": 70,
        "normal": 40,
        "low": 0
    }
    
    LEVEL_COLORS = {
        "high": "#22c55e",    # 초록
        "normal": "#eab308",  # 노랑
        "low": "#ef4444"      # 빨강
    }
    
    LEVEL_EMOJIS = {
        "high": "🟢",
        "normal": "🟡",
        "low": "🔴"
    }
    
    def __init__(self, segment_duration: float = 10.0):
        self.segment_duration = segment_duration
        self.segments: List[EngagementSegment] = []
    
    def analyze(
        self,
        vision_timeline: List[Dict],
        vibe_timeline: List[Dict],
        content_timeline: List[Dict],
        duration: float
    ) -> List[EngagementSegment]:
        """
        전체 강의의 몰입도 분석
        
        Returns:
            EngagementSegment 리스트
        """
        self.segments = []
        
        current_time = 0
        while current_time < duration:
            end_time = min(current_time + self.segment_duration, duration)
            
            segment = self._analyze_segment(
                current_time, end_time,
                vision_timeline, vibe_timeline, content_timeline
            )
            
            self.segments.append(segment)
            current_time = end_time
        
        return self.segments
    
    def _analyze_segment(
        self,
        start: float,
        end: float,
        vision_timeline: List[Dict],
        vibe_timeline: List[Dict],
        content_timeline: List[Dict]
    ) -> EngagementSegment:
        """단일 세그먼트 분석"""
        
        # 해당 시간대 데이터 필터링
        vision_data = [v for v in vision_timeline if start <= v.get("timestamp", 0) < end]
        vibe_data = [v for v in vibe_timeline if start <= v.get("start", 0) < end]
        content_data = [c for c in content_timeline if start <= c.get("timestamp", 0) < end]
        
        factors = {}
        
        # 1. 제스처 점수
        if vision_data:
            factors["gesture"] = np.mean([v.get("gesture_score", 0) for v in vision_data])
        else:
            factors["gesture"] = 50
        
        # 2. 음성 다양성 (비단조로움)
        if vibe_data:
            monotone_count = sum(1 for v in vibe_data if v.get("is_monotone", False))
            factors["voice_variety"] = (1 - monotone_count / max(1, len(vibe_data))) * 100
        else:
            factors["voice_variety"] = 50
        
        # 3. 시선 접촉
        if vision_data:
            eye_contact = sum(1 for v in vision_data if v.get("eye_contact", False))
            factors["eye_contact"] = (eye_contact / max(1, len(vision_data))) * 100
        else:
            factors["eye_contact"] = 50
        
        # 4. 콘텐츠 명확성 (텍스트 밀도 5가 최적)
        if content_data:
            avg_density = np.mean([c.get("text_density_score", 5) for c in content_data])
            # 5에 가까울수록 100점
            factors["content_clarity"] = max(0, 100 - abs(avg_density - 5) * 20)
        else:
            factors["content_clarity"] = 50
        
        # 5. 표정 활력
        if vision_data:
            factors["expression"] = np.mean([v.get("expression_score", 50) for v in vision_data])
        else:
            factors["expression"] = 50
        
        # 가중 평균으로 종합 점수 계산
        score = sum(
            factors.get(factor, 50) * weight
            for factor, weight in self.FACTOR_WEIGHTS.items()
        )
        
        # 레벨 결정
        if score >= self.LEVEL_THRESHOLDS["high"]:
            level = "high"
        elif score >= self.LEVEL_THRESHOLDS["normal"]:
            level = "normal"
        else:
            level = "low"
        
        return EngagementSegment(
            start_time=start,
            end_time=end,
            score=round(score, 1),
            level=level,
            factors=factors
        )
    
    def get_heatmap_data(self) -> List[Dict]:
        """히트맵용 데이터 반환"""
        return [
            {
                "start": s.start_time,
                "end": s.end_time,
                "score": s.score,
                "level": s.level,
                "color": self.LEVEL_COLORS[s.level],
                "emoji": self.LEVEL_EMOJIS[s.level]
            }
            for s in self.segments
        ]
    
    def get_text_heatmap(self, max_width: int = 50) -> str:
        """텍스트 기반 히트맵 문자열 생성"""
        if not self.segments:
            return ""
        
        # 세그먼트를 이모지로 변환
        emojis = [self.LEVEL_EMOJIS[s.level] for s in self.segments]
        
        # 너무 길면 축약
        if len(emojis) > max_width:
            step = len(emojis) / max_width
            sampled = [emojis[int(i * step)] for i in range(max_width)]
            return "".join(sampled)
        
        return "".join(emojis)
    
    def find_death_valleys(self, min_duration: float = 30.0) -> List[Tuple[float, float]]:
        """연속된 낮은 몰입도 구간 (Death Valley) 찾기"""
        valleys = []
        valley_start = None
        
        for segment in self.segments:
            if segment.level == "low":
                if valley_start is None:
                    valley_start = segment.start_time
            else:
                if valley_start is not None:
                    valley_end = segment.start_time
                    if valley_end - valley_start >= min_duration:
                        valleys.append((valley_start, valley_end))
                    valley_start = None
        
        # 마지막 세그먼트 처리
        if valley_start is not None and self.segments:
            valley_end = self.segments[-1].end_time
            if valley_end - valley_start >= min_duration:
                valleys.append((valley_start, valley_end))
        
        return valleys
    
    def find_peak_moments(self, top_n: int = 5) -> List[Tuple[float, float]]:
        """가장 몰입도가 높은 구간 찾기"""
        if not self.segments:
            return []
        
        sorted_segments = sorted(self.segments, key=lambda s: s.score, reverse=True)
        return [
            (s.start_time, s.end_time)
            for s in sorted_segments[:top_n]
        ]
    
    def get_summary(self) -> Dict:
        """몰입도 분석 요약"""
        if not self.segments:
            return {"error": "분석 결과가 없습니다"}
        
        scores = [s.score for s in self.segments]
        levels = [s.level for s in self.segments]
        total = len(self.segments)
        
        return {
            "average_score": round(np.mean(scores), 1),
            "min_score": round(min(scores), 1),
            "max_score": round(max(scores), 1),
            "level_distribution": {
                "high": levels.count("high") / total,
                "normal": levels.count("normal") / total,
                "low": levels.count("low") / total
            },
            "death_valley_count": len(self.find_death_valleys()),
            "peak_moment_count": levels.count("high"),
            "text_heatmap": self.get_text_heatmap()
        }
    
    def format_time(self, seconds: float) -> str:
        """초를 MM:SS 형식으로"""
        return str(timedelta(seconds=int(seconds)))[2:7]
