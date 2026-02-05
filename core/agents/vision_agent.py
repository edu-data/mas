"""
👁️ Vision Agent - 강사 비언어 행동 분석
OpenCV + 간소화된 분석 (MediaPipe 호환성 이슈로 인해)
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class VisionMetrics:
    """비전 분석 결과 메트릭"""
    timestamp: float
    gesture_active: bool = False           # 제스처 활성화 여부
    gesture_score: float = 0.0             # 제스처 역동성 점수 (0-100)
    hand_position: str = "unknown"         # low, mid, high
    eye_contact: bool = False              # 정면 응시 여부
    face_detected: bool = False            # 얼굴 감지 여부
    expression_score: float = 50.0         # 표정 활력 점수 (0-100)
    body_openness: float = 0.5             # 자세 개방성 (0-1)
    motion_score: float = 0.0              # 움직임 점수


class VisionAgent:
    """
    👁️ Vision Agent
    강사의 비언어적 요소(제스처, 시선, 표정)를 분석
    OpenCV 기반 간소화 버전 (MediaPipe 의존성 제거)
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {
            "gesture_threshold": 0.6,
            "face_confidence": 0.5
        }
        
        # OpenCV 얼굴 감지기
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # 움직임 감지를 위한 이전 프레임
        self.prev_frame = None
        self.prev_gray = None
        
        # 분석 결과 저장
        self.results: List[VisionMetrics] = []
    
    def analyze_frame(self, frame: np.ndarray, timestamp: float) -> VisionMetrics:
        """
        단일 프레임의 비언어적 요소 분석
        
        Args:
            frame: BGR 이미지 (OpenCV 형식)
            timestamp: 프레임 타임스탬프 (초)
            
        Returns:
            VisionMetrics 객체
        """
        metrics = VisionMetrics(timestamp=timestamp)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. 얼굴 감지
        self._analyze_face(frame, gray, metrics)
        
        # 2. 움직임 분석 (제스처 대용)
        self._analyze_motion(gray, metrics)
        
        # 3. 프레임 영역별 활동성 분석
        self._analyze_regions(frame, metrics)
        
        # 이전 프레임 저장
        self.prev_frame = frame.copy()
        self.prev_gray = gray.copy()
        
        self.results.append(metrics)
        return metrics
    
    def _analyze_face(self, frame: np.ndarray, gray: np.ndarray, metrics: VisionMetrics):
        """얼굴 감지 및 분석"""
        height, width = frame.shape[:2]
        
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=4,
            minSize=(30, 30)
        )
        
        if len(faces) > 0:
            metrics.face_detected = True
            
            # 가장 큰 얼굴 선택
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            
            # 얼굴 중심 위치로 시선 추정
            face_center_x = (x + w // 2) / width
            face_center_y = (y + h // 2) / height
            
            # 중앙에 가까우면 정면 응시로 판단
            is_centered = 0.3 < face_center_x < 0.7
            metrics.eye_contact = is_centered
            
            # 얼굴 크기로 표정 활력 추정
            # (얼굴이 크게 보이면 카메라에 가까이 = 더 적극적)
            face_size_ratio = (w * h) / (width * height)
            metrics.expression_score = min(100, face_size_ratio * 1000)
    
    def _analyze_motion(self, gray: np.ndarray, metrics: VisionMetrics):
        """움직임 분석 (제스처 대용)"""
        if self.prev_gray is None:
            return
        
        # 프레임 차이 계산
        diff = cv2.absdiff(gray, self.prev_gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        # 움직임 비율 계산
        motion_pixels = np.count_nonzero(thresh)
        total_pixels = thresh.size
        motion_ratio = motion_pixels / total_pixels
        
        # 움직임 점수 (0-100)
        metrics.motion_score = min(100, motion_ratio * 500)
        
        # 움직임이 충분하면 제스처 활성화로 판단
        metrics.gesture_active = motion_ratio > 0.02
        metrics.gesture_score = metrics.motion_score
    
    def _analyze_regions(self, frame: np.ndarray, metrics: VisionMetrics):
        """프레임 영역별 분석"""
        height, width = frame.shape[:2]
        
        # 상하 영역 분할
        top_half = frame[:height//2, :]
        bottom_half = frame[height//2:, :]
        
        # 각 영역의 활동성 (엣지 밀도)
        top_edges = cv2.Canny(cv2.cvtColor(top_half, cv2.COLOR_BGR2GRAY), 50, 150)
        bottom_edges = cv2.Canny(cv2.cvtColor(bottom_half, cv2.COLOR_BGR2GRAY), 50, 150)
        
        top_activity = np.count_nonzero(top_edges) / top_edges.size
        bottom_activity = np.count_nonzero(bottom_edges) / bottom_edges.size
        
        # 상단 활동이 많으면 손이 위에 있는 것으로 추정
        if top_activity > bottom_activity * 1.5:
            metrics.hand_position = "high"
        elif bottom_activity > top_activity * 1.5:
            metrics.hand_position = "low"
        else:
            metrics.hand_position = "mid"
        
        # 자세 개방성 추정
        # 프레임 전체에 활동이 고르게 분포하면 개방적
        metrics.body_openness = min(1.0, (top_activity + bottom_activity) * 10)
    
    def get_summary(self) -> Dict:
        """분석 결과 요약"""
        if not self.results:
            return {"error": "분석 결과가 없습니다"}
        
        total = len(self.results)
        
        return {
            "total_frames_analyzed": total,
            "gesture_active_ratio": sum(1 for r in self.results if r.gesture_active) / total,
            "avg_gesture_score": np.mean([r.gesture_score for r in self.results]),
            "eye_contact_ratio": sum(1 for r in self.results if r.eye_contact) / total,
            "face_detection_ratio": sum(1 for r in self.results if r.face_detected) / total,
            "avg_expression_score": np.mean([r.expression_score for r in self.results]),
            "avg_body_openness": np.mean([r.body_openness for r in self.results]),
            "avg_motion_score": np.mean([r.motion_score for r in self.results]),
            "hand_position_distribution": self._get_hand_distribution()
        }
    
    def _get_hand_distribution(self) -> Dict[str, float]:
        """손 위치 분포"""
        if not self.results:
            return {}
        
        positions = [r.hand_position for r in self.results]
        total = len(positions)
        
        return {
            "high": positions.count("high") / total,
            "mid": positions.count("mid") / total,
            "low": positions.count("low") / total
        }
    
    def get_timeline(self) -> List[Dict]:
        """시간별 분석 결과"""
        return [
            {
                "timestamp": r.timestamp,
                "gesture_score": r.gesture_score,
                "eye_contact": r.eye_contact,
                "expression_score": r.expression_score,
                "motion_score": r.motion_score
            }
            for r in self.results
        ]
    
    def reset(self):
        """분석 결과 초기화"""
        self.results = []
        self.prev_frame = None
        self.prev_gray = None
