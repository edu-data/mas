"""
🧠 Master Agent - 종합 평가 및 피드백 생성
3개 Sub-Agent 결과를 통합하여 고차원 분석 수행
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import timedelta


@dataclass
class SegmentAnalysis:
    """구간별 종합 분석 결과"""
    start_time: float
    end_time: float
    engagement_score: float = 50.0      # 몰입도 점수 (0-100)
    engagement_level: str = "normal"     # low, normal, high
    is_death_valley: bool = False        # 지루함 극대화 구간
    incongruence_detected: bool = False  # 언행불일치 감지
    incongruence_details: str = ""       # 불일치 상세 내용
    recommendations: List[str] = field(default_factory=list)


@dataclass
class LectureReport:
    """강의 종합 리포트"""
    total_duration: float
    overall_score: float
    dimension_scores: Dict[str, float]
    death_valleys: List[Tuple[float, float]]
    incongruences: List[Dict]
    engagement_timeline: List[Dict]
    top_issues: List[str]
    recommendations: List[str]
    strengths: List[str]


class MasterAgent:
    """
    🧠 Master Agent
    Vision, Content, Vibe Agent의 결과를 통합하여 종합 평가 수행
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {
            "death_valley_duration": 30,    # 연속 지루함 구간 최소 초
            "incongruence_threshold": 0.5,  # 불일치 감지 임계값
            "segment_duration": 10.0        # 분석 세그먼트 길이
        }
        
        # 135점 평가 프레임워크 가중치
        self.framework_weights = {
            "수업_전달": 0.35,       # 45/135
            "수업_설계": 0.22,       # 30/135
            "학습자_참여": 0.22,     # 30/135
            "평가_및_정리": 0.21     # 30/135 (근사)
        }
        
        self.segments: List[SegmentAnalysis] = []
    
    def synthesize(
        self,
        vision_summary: Dict,
        content_summary: Dict,
        vibe_summary: Dict,
        vision_timeline: List[Dict],
        content_timeline: List[Dict],
        vibe_timeline: List[Dict],
        duration: float
    ) -> LectureReport:
        """
        모든 Agent 결과를 종합하여 최종 리포트 생성
        
        Args:
            vision_summary: VisionAgent.get_summary() 결과
            content_summary: ContentAgent.get_summary() 결과
            vibe_summary: VibeAgent.get_summary() 결과
            *_timeline: 각 Agent의 시간별 분석 결과
            duration: 전체 강의 길이 (초)
            
        Returns:
            LectureReport 객체
        """
        # 1. 구간별 종합 분석
        self._analyze_segments(vision_timeline, content_timeline, vibe_timeline, duration)
        
        # 2. Death Valley 탐지
        death_valleys = self._find_death_valleys()
        
        # 3. 언행불일치 탐지
        incongruences = self._detect_incongruences(vision_timeline, vibe_timeline)
        
        # 4. 차원별 점수 계산
        dimension_scores = self._calculate_dimension_scores(
            vision_summary, content_summary, vibe_summary
        )
        
        # 5. 종합 점수 계산
        overall_score = self._calculate_overall_score(dimension_scores)
        
        # 6. 주요 이슈 및 권고사항 생성
        top_issues = self._generate_issues(
            vision_summary, content_summary, vibe_summary,
            death_valleys, incongruences
        )
        recommendations = self._generate_recommendations(top_issues)
        strengths = self._identify_strengths(
            vision_summary, content_summary, vibe_summary
        )
        
        # 7. 몰입도 타임라인 생성
        engagement_timeline = self._create_engagement_timeline()
        
        return LectureReport(
            total_duration=duration,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            death_valleys=death_valleys,
            incongruences=incongruences,
            engagement_timeline=engagement_timeline,
            top_issues=top_issues,
            recommendations=recommendations,
            strengths=strengths
        )
    
    def _analyze_segments(
        self,
        vision_timeline: List[Dict],
        content_timeline: List[Dict],
        vibe_timeline: List[Dict],
        duration: float
    ):
        """구간별 종합 분석"""
        segment_duration = self.config["segment_duration"]
        self.segments = []
        
        current_time = 0
        while current_time < duration:
            end_time = min(current_time + segment_duration, duration)
            
            # 해당 구간의 데이터 수집
            vision_data = [v for v in vision_timeline 
                         if current_time <= v.get("timestamp", 0) < end_time]
            vibe_data = [v for v in vibe_timeline 
                        if current_time <= v.get("start", 0) < end_time]
            content_data = [c for c in content_timeline 
                          if current_time <= c.get("timestamp", 0) < end_time]
            
            # 몰입도 점수 계산
            engagement_score = self._calculate_segment_engagement(
                vision_data, vibe_data, content_data
            )
            
            # 몰입도 레벨 분류
            if engagement_score < 30:
                level = "low"
            elif engagement_score > 70:
                level = "high"
            else:
                level = "normal"
            
            segment = SegmentAnalysis(
                start_time=current_time,
                end_time=end_time,
                engagement_score=engagement_score,
                engagement_level=level,
                is_death_valley=(level == "low")
            )
            
            self.segments.append(segment)
            current_time = end_time
    
    def _calculate_segment_engagement(
        self,
        vision_data: List[Dict],
        vibe_data: List[Dict],
        content_data: List[Dict]
    ) -> float:
        """구간 몰입도 점수 계산"""
        scores = []
        
        # 제스처 점수
        if vision_data:
            avg_gesture = np.mean([v.get("gesture_score", 0) for v in vision_data])
            scores.append(avg_gesture)
        
        # 음성 다양성 점수
        if vibe_data:
            # 단조롭지 않을수록 높은 점수
            monotone_count = sum(1 for v in vibe_data if v.get("is_monotone", False))
            voice_variety = (1 - monotone_count / max(1, len(vibe_data))) * 100
            scores.append(voice_variety)
        
        # 콘텐츠 점수 (텍스트 과다 = 낮은 점수)
        if content_data:
            avg_density_score = np.mean([c.get("text_density_score", 5) for c in content_data])
            # 밀도 5 최적, 10이면 0점
            content_score = max(0, (10 - avg_density_score) * 10)
            scores.append(content_score)
        
        if scores:
            return np.mean(scores)
        return 50.0
    
    def _find_death_valleys(self) -> List[Tuple[float, float]]:
        """지루함이 극대화된 구간(Death Valley) 탐지"""
        death_valleys = []
        min_duration = self.config["death_valley_duration"]
        
        # 연속된 낮은 몰입도 구간 찾기
        valley_start = None
        
        for segment in self.segments:
            if segment.engagement_level == "low":
                if valley_start is None:
                    valley_start = segment.start_time
            else:
                if valley_start is not None:
                    valley_end = segment.start_time
                    if valley_end - valley_start >= min_duration:
                        death_valleys.append((valley_start, valley_end))
                    valley_start = None
        
        # 마지막 구간이 Death Valley인 경우
        if valley_start is not None:
            if self.segments and self.segments[-1].end_time - valley_start >= min_duration:
                death_valleys.append((valley_start, self.segments[-1].end_time))
        
        return death_valleys
    
    def _detect_incongruences(
        self,
        vision_timeline: List[Dict],
        vibe_timeline: List[Dict]
    ) -> List[Dict]:
        """언행불일치 탐지"""
        incongruences = []
        
        # 비전과 바이브 데이터를 시간으로 매칭
        for vibe in vibe_timeline:
            start = vibe.get("start", 0)
            end = vibe.get("end", 0)
            
            # 해당 시간대의 비전 데이터 찾기
            matching_vision = [
                v for v in vision_timeline
                if start <= v.get("timestamp", 0) < end
            ]
            
            if not matching_vision:
                continue
            
            # 불일치 패턴 1: 높은 에너지 음성 + 제스처 없음
            high_energy = vibe.get("energy_mean", 0) > 0.08
            avg_gesture = np.mean([v.get("gesture_score", 0) for v in matching_vision])
            low_gesture = avg_gesture < 20
            
            if high_energy and low_gesture:
                incongruences.append({
                    "timestamp": start,
                    "type": "energy_gesture_mismatch",
                    "description": "높은 에너지 음성이지만 제스처가 거의 없음",
                    "suggestion": "목소리의 강조와 함께 손 제스처를 활용하세요"
                })
            
            # 불일치 패턴 2: 흥분된 어조 + 시선 회피
            pitch_high = vibe.get("pitch_std", 0) > 30  # 피치 변화 큼 = 흥분
            avg_eye_contact = np.mean([
                1 if v.get("eye_contact", False) else 0 
                for v in matching_vision
            ])
            no_eye_contact = avg_eye_contact < 0.3
            
            if pitch_high and no_eye_contact:
                incongruences.append({
                    "timestamp": start,
                    "type": "excitement_eye_contact_mismatch",
                    "description": "열정적인 어조이지만 시선이 청중을 향하지 않음",
                    "suggestion": "카메라를 직접 바라보며 말씀하세요"
                })
        
        return incongruences
    
    def _calculate_dimension_scores(
        self,
        vision_summary: Dict,
        content_summary: Dict,
        vibe_summary: Dict
    ) -> Dict[str, float]:
        """
        초등임용 2차 수업실연 채점 기준 + 좋은 수업 프레임워크 통합 평가
        
        7개 대영역, 12개 세부항목 (총 100점)
        """
        scores = {}
        
        # ===== 1. 수업 전문성 (20점) =====
        # 1-1. 학습 목표 명료성 (10점) - 도입부 음성 활성도로 추정
        intro_energy = vibe_summary.get("energy_mean", 0.5)
        goal_clarity = min(10, intro_energy * 15)
        
        # 1-2. 학습 내용 충실성 (10점) - 시각자료 밀도로 추정
        high_density = content_summary.get("high_density_ratio", 0.3)
        content_fidelity = min(10, (1 - high_density * 0.5) * 10)
        
        scores["수업_전문성"] = {
            "학습목표_명료성": round(goal_clarity, 1),
            "학습내용_충실성": round(content_fidelity, 1),
            "소계": round(goal_clarity + content_fidelity, 1)
        }
        
        # ===== 2. 교수-학습 방법 (20점) =====
        # 2-1. 교수법 다양성 (10점) - 제스처 + 시선 활용
        gesture_ratio = vision_summary.get("gesture_active_ratio", 0)
        eye_contact = vision_summary.get("eye_contact_ratio", 0)
        method_diversity = min(10, (gesture_ratio + eye_contact) * 10)
        
        # 2-2. 학습 활동 효과성 (10점) - 침묵 비율 (적절한 휴지기)
        silence = vibe_summary.get("avg_silence_ratio", 0.2)
        ideal_silence = 0.15
        activity_effect = max(0, 10 - abs(silence - ideal_silence) * 50)
        
        scores["교수학습_방법"] = {
            "교수법_다양성": round(method_diversity, 1),
            "학습활동_효과성": round(activity_effect, 1),
            "소계": round(method_diversity + activity_effect, 1)
        }
        
        # ===== 3. 판서 및 언어 사용 (15점) =====
        # 3-1. 판서 가독성 (5점) - 텍스트 밀도 역비례
        text_density = content_summary.get("avg_text_complexity", 50)
        readability = max(0, 5 - (text_density / 100) * 3)
        
        # 3-2. 언어 명료성 (5점) - 단조로움 역비례
        monotone = vibe_summary.get("monotone_ratio", 0.5)
        language_clarity = max(0, 5 - monotone * 5)
        
        # 3-3. 발화 속도 적절성 (5점) - 피치 다양성
        pitch_std = vibe_summary.get("pitch_std", 20)
        speech_pace = min(5, pitch_std / 10)
        
        scores["판서_언어"] = {
            "판서_가독성": round(readability, 1),
            "언어_명료성": round(language_clarity, 1),
            "발화속도_적절성": round(speech_pace, 1),
            "소계": round(readability + language_clarity + speech_pace, 1)
        }
        
        # ===== 4. 수업 태도 (15점) =====
        # 4-1. 교사 열정 (5점) - 에너지 레벨
        energy = vibe_summary.get("energy_mean", 0.3)
        enthusiasm = min(5, energy * 8)
        
        # 4-2. 학생 소통 (5점) - 아이컨택
        student_comm = min(5, eye_contact * 10)
        
        # 4-3. 자신감 (5점) - 제스처 활성도
        confidence = min(5, gesture_ratio * 10)
        
        scores["수업_태도"] = {
            "교사_열정": round(enthusiasm, 1),
            "학생_소통": round(student_comm, 1),
            "자신감": round(confidence, 1),
            "소계": round(enthusiasm + student_comm + confidence, 1)
        }
        
        # ===== 5. 학생 참여 유도 (15점) =====
        # 5-1. 질문 기법 (7.5점) - 표정 점수로 추정
        expression = vision_summary.get("avg_expression_score", 50)
        questioning = min(7.5, expression / 100 * 7.5)
        
        # 5-2. 피드백 제공 (7.5점) - 침묵 후 발화 패턴
        feedback = min(7.5, (1 - monotone) * 7.5)
        
        scores["학생_참여유도"] = {
            "질문_기법": round(questioning, 1),
            "피드백_제공": round(feedback, 1),
            "소계": round(questioning + feedback, 1)
        }
        
        # ===== 6. 시간 배분 (10점) =====
        # 전체 시간 대비 침묵/발화 균형
        speech_ratio = 1 - silence
        ideal_speech = 0.75  # 75% 발화
        time_balance = max(0, 10 - abs(speech_ratio - ideal_speech) * 30)
        
        scores["시간_배분"] = {
            "시간_균형": round(time_balance, 1),
            "소계": round(time_balance, 1)
        }
        
        # ===== 7. 창의성 및 차별화 (5점) =====
        # 제스처 + 표정 + 톤 다양성 복합
        creativity_factors = [
            gesture_ratio * 100,
            expression,
            (1 - monotone) * 100
        ]
        creativity = min(5, np.mean(creativity_factors) / 100 * 5)
        
        scores["창의성_차별화"] = {
            "수업_창의성": round(creativity, 1),
            "소계": round(creativity, 1)
        }
        
        # ===== 총점 계산 =====
        total = sum(dim["소계"] for dim in scores.values())
        scores["총점"] = round(total, 1)
        
        # 환산 점수 (100점 만점)
        scores["환산_점수"] = round(total, 1)  # 이미 100점 기준
        
        return scores
    
    def _calculate_overall_score(self, dimension_scores: Dict[str, float]) -> float:
        """총점 반환 (100점 만점)"""
        # 새 형식: scores["총점"] 직접 사용
        if "총점" in dimension_scores:
            return dimension_scores["총점"]
        
        # 구형식 폴백
        total = 0
        for dim, weight in self.framework_weights.items():
            total += dimension_scores.get(dim, 50) * weight
        return round(total, 1)
    
    def _generate_issues(
        self,
        vision_summary: Dict,
        content_summary: Dict,
        vibe_summary: Dict,
        death_valleys: List,
        incongruences: List
    ) -> List[str]:
        """주요 이슈 목록 생성"""
        issues = []
        
        # Death Valley 이슈
        if death_valleys:
            for start, end in death_valleys[:3]:
                time_str = self._format_time_range(start, end)
                issues.append(f"🔴 Death Valley 구간: {time_str} - 몰입도가 급격히 낮음")
        
        # 언행불일치 이슈
        for inc in incongruences[:3]:
            time_str = self._format_time(inc["timestamp"])
            issues.append(f"⚠️ 언행불일치 [{time_str}]: {inc['description']}")
        
        # 비전 관련 이슈
        if vision_summary.get("gesture_active_ratio", 0) < 0.3:
            issues.append("⚠️ 제스처 활용이 부족합니다 (30% 미만 구간만 활성화)")
        
        # 콘텐츠 관련 이슈
        for warning in content_summary.get("warnings", []):
            issues.append(warning)
        
        # 바이브 관련 이슈
        for warning in vibe_summary.get("warnings", []):
            issues.append(warning)
        
        return issues[:10]  # 상위 10개만
    
    def _generate_recommendations(self, issues: List[str]) -> List[str]:
        """이슈 기반 권고사항 생성"""
        recommendations = []
        
        for issue in issues:
            if "Death Valley" in issue:
                recommendations.append(
                    "💡 지루함 구간에서는 질문을 던지거나 실습 시간을 추가하세요"
                )
            elif "제스처" in issue:
                recommendations.append(
                    "💡 중요 포인트에서 손을 어깨 높이로 올려 강조하세요"
                )
            elif "단조로운" in issue:
                recommendations.append(
                    "💡 핵심 단어에서 목소리 톤을 높이고 2초 휴지기를 활용하세요"
                )
            elif "텍스트 과다" in issue:
                recommendations.append(
                    "💡 슬라이드당 텍스트를 50자 이내로 줄이고 이미지를 활용하세요"
                )
            elif "시선" in issue or "eye contact" in issue.lower():
                recommendations.append(
                    "💡 카메라를 직접 바라보며 청중과 소통하는 느낌을 주세요"
                )
        
        # 중복 제거
        return list(dict.fromkeys(recommendations))[:5]
    
    def _identify_strengths(
        self,
        vision_summary: Dict,
        content_summary: Dict,
        vibe_summary: Dict
    ) -> List[str]:
        """강점 식별"""
        strengths = []
        
        if vision_summary.get("gesture_active_ratio", 0) > 0.6:
            strengths.append("✅ 활발한 제스처 활용으로 역동적인 전달력")
        
        if vision_summary.get("eye_contact_ratio", 0) > 0.7:
            strengths.append("✅ 뛰어난 시선 처리로 청중과의 연결감")
        
        if vibe_summary.get("monotone_ratio", 1) < 0.2:
            strengths.append("✅ 다양한 음성 톤으로 지루함 방지")
        
        if content_summary.get("high_density_ratio", 1) < 0.1:
            strengths.append("✅ 깔끔한 슬라이드 구성으로 가독성 확보")
        
        ideal_min, ideal_max = 0.1, 0.3
        silence = vibe_summary.get("avg_silence_ratio", 0)
        if ideal_min <= silence <= ideal_max:
            strengths.append("✅ 적절한 휴지기 활용으로 내용 소화 시간 제공")
        
        return strengths[:3]
    
    def _create_engagement_timeline(self) -> List[Dict]:
        """몰입도 타임라인 생성"""
        return [
            {
                "start": s.start_time,
                "end": s.end_time,
                "score": s.engagement_score,
                "level": s.engagement_level,
                "color": self._level_to_color(s.engagement_level)
            }
            for s in self.segments
        ]
    
    def _level_to_color(self, level: str) -> str:
        """몰입도 레벨을 색상으로 변환"""
        colors = {
            "high": "#22c55e",    # 초록
            "normal": "#eab308",  # 노랑
            "low": "#ef4444"      # 빨강
        }
        return colors.get(level, "#9ca3af")
    
    def _format_time(self, seconds: float) -> str:
        """초를 MM:SS 형식으로 변환"""
        return str(timedelta(seconds=int(seconds)))[2:7]
    
    def _format_time_range(self, start: float, end: float) -> str:
        """시간 범위 포맷"""
        return f"{self._format_time(start)} ~ {self._format_time(end)}"
