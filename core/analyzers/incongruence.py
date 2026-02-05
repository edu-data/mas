"""
🚨 Incongruence Detector - 언행불일치 감지
Vision과 Vibe 데이터를 비교하여 말과 행동의 불일치 탐지
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class Incongruence:
    """언행불일치 정보"""
    timestamp: float
    type: str
    severity: str       # low, medium, high
    description: str
    visual_state: str
    audio_state: str
    suggestion: str


class IncongruenceDetector:
    """
    언행불일치 패턴 감지기
    
    감지 패턴:
    1. 높은 에너지 음성 + 제스처 없음
    2. 흥분된 어조 + 무표정
    3. 강조 + 시선 회피
    4. 중요 발언 + 손 주머니
    """
    
    # 불일치 패턴 정의
    PATTERNS = {
        "energy_gesture": {
            "name": "에너지-제스처 불일치",
            "description": "목소리는 힘차지만 몸은 얼어있음",
            "suggestion": "손을 활용해 말의 에너지를 시각적으로 표현하세요"
        },
        "excitement_expression": {
            "name": "흥분-표정 불일치",
            "description": "열정적으로 말하지만 표정이 경직됨",
            "suggestion": "자연스러운 미소와 함께 말씀하세요"
        },
        "emphasis_eye": {
            "name": "강조-시선 불일치",
            "description": "중요한 내용을 말하면서 시선 회피",
            "suggestion": "핵심 포인트에서 카메라를 똑바로 바라보세요"
        },
        "volume_posture": {
            "name": "음량-자세 불일치",
            "description": "큰 소리로 말하지만 자세가 움츠러듦",
            "suggestion": "어깨를 펴고 열린 자세로 전달하세요"
        }
    }
    
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.detections: List[Incongruence] = []
    
    def detect(
        self,
        vision_timeline: List[Dict],
        vibe_timeline: List[Dict],
        time_tolerance: float = 5.0
    ) -> List[Incongruence]:
        """
        타임라인 데이터에서 언행불일치 탐지
        
        Args:
            vision_timeline: VisionAgent 시간별 데이터
            vibe_timeline: VibeAgent 시간별 데이터
            time_tolerance: 매칭 허용 시간 (초)
            
        Returns:
            탐지된 Incongruence 리스트
        """
        self.detections = []
        
        for vibe in vibe_timeline:
            start = vibe.get("start", 0)
            end = vibe.get("end", 0)
            
            # 해당 시간대의 비전 데이터 매칭
            matching_vision = self._get_matching_vision(
                vision_timeline, start, end
            )
            
            if not matching_vision:
                continue
            
            # 패턴 1: 에너지-제스처 불일치
            self._check_energy_gesture(vibe, matching_vision, start)
            
            # 패턴 2: 흥분-표정 불일치
            self._check_excitement_expression(vibe, matching_vision, start)
            
            # 패턴 3: 강조-시선 불일치
            self._check_emphasis_eye(vibe, matching_vision, start)
            
            # 패턴 4: 음량-자세 불일치
            self._check_volume_posture(vibe, matching_vision, start)
        
        return self.detections
    
    def _get_matching_vision(
        self,
        vision_timeline: List[Dict],
        start: float,
        end: float
    ) -> List[Dict]:
        """시간 범위에 해당하는 비전 데이터 반환"""
        return [
            v for v in vision_timeline
            if start <= v.get("timestamp", 0) < end
        ]
    
    def _check_energy_gesture(
        self,
        vibe: Dict,
        vision_data: List[Dict],
        timestamp: float
    ):
        """에너지-제스처 불일치 체크"""
        high_energy = vibe.get("energy_mean", 0) > 0.08
        
        if not high_energy:
            return
        
        avg_gesture = np.mean([v.get("gesture_score", 0) for v in vision_data])
        
        if avg_gesture < 20:
            pattern = self.PATTERNS["energy_gesture"]
            self.detections.append(Incongruence(
                timestamp=timestamp,
                type="energy_gesture",
                severity="medium",
                description=pattern["description"],
                visual_state=f"제스처 점수: {avg_gesture:.0f}/100",
                audio_state=f"에너지: 높음 ({vibe.get('energy_mean', 0):.3f})",
                suggestion=pattern["suggestion"]
            ))
    
    def _check_excitement_expression(
        self,
        vibe: Dict,
        vision_data: List[Dict],
        timestamp: float
    ):
        """흥분-표정 불일치 체크"""
        pitch_variety = vibe.get("pitch_std", 0) > 25
        
        if not pitch_variety:
            return
        
        avg_expression = np.mean([v.get("expression_score", 50) for v in vision_data])
        
        if avg_expression < 40:
            pattern = self.PATTERNS["excitement_expression"]
            self.detections.append(Incongruence(
                timestamp=timestamp,
                type="excitement_expression",
                severity="medium",
                description=pattern["description"],
                visual_state=f"표정 점수: {avg_expression:.0f}/100",
                audio_state=f"피치 변화: 활발 ({vibe.get('pitch_std', 0):.1f})",
                suggestion=pattern["suggestion"]
            ))
    
    def _check_emphasis_eye(
        self,
        vibe: Dict,
        vision_data: List[Dict],
        timestamp: float
    ):
        """강조-시선 불일치 체크"""
        # 높은 에너지 + 높은 피치 변화 = 강조
        is_emphasis = (
            vibe.get("energy_mean", 0) > 0.06 and
            vibe.get("pitch_std", 0) > 20
        )
        
        if not is_emphasis:
            return
        
        eye_contact_ratio = np.mean([
            1 if v.get("eye_contact", False) else 0
            for v in vision_data
        ])
        
        if eye_contact_ratio < 0.3:
            pattern = self.PATTERNS["emphasis_eye"]
            self.detections.append(Incongruence(
                timestamp=timestamp,
                type="emphasis_eye",
                severity="high",
                description=pattern["description"],
                visual_state=f"시선 접촉: {eye_contact_ratio*100:.0f}%",
                audio_state="강조 어조 감지됨",
                suggestion=pattern["suggestion"]
            ))
    
    def _check_volume_posture(
        self,
        vibe: Dict,
        vision_data: List[Dict],
        timestamp: float
    ):
        """음량-자세 불일치 체크"""
        high_volume = vibe.get("energy_mean", 0) > 0.1
        
        if not high_volume:
            return
        
        # 자세 개방성이 낮은지 확인 (VisionAgent에서 제공하는 경우)
        # 현재는 제스처 점수로 대체
        avg_gesture = np.mean([v.get("gesture_score", 0) for v in vision_data])
        
        if avg_gesture < 15:
            pattern = self.PATTERNS["volume_posture"]
            self.detections.append(Incongruence(
                timestamp=timestamp,
                type="volume_posture",
                severity="medium",
                description=pattern["description"],
                visual_state="움츠러든 자세",
                audio_state="큰 음량",
                suggestion=pattern["suggestion"]
            ))
    
    def get_summary(self) -> Dict:
        """탐지 결과 요약"""
        if not self.detections:
            return {"total": 0, "message": "언행불일치가 감지되지 않았습니다"}
        
        by_type = {}
        by_severity = {"low": 0, "medium": 0, "high": 0}
        
        for d in self.detections:
            by_type[d.type] = by_type.get(d.type, 0) + 1
            by_severity[d.severity] += 1
        
        return {
            "total": len(self.detections),
            "by_type": by_type,
            "by_severity": by_severity,
            "worst_timestamps": [d.timestamp for d in self.detections if d.severity == "high"]
        }
