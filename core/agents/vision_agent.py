"""
👁️ Vision Agent - 강사 비언어 행동 분석
v5.0: MediaPipe Face Mesh + Pose Estimation 기반 (OpenCV 폴백 유지)
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

# MediaPipe graceful import
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False


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
    # v5.0 추가 필드
    gaze_direction: str = "center"         # left, center, right
    shoulder_angle: float = 0.0            # 어깨 각도 (자세)
    arm_gesture_type: str = "none"         # none, pointing, open, closed
    head_tilt: float = 0.0                 # 머리 기울기 (도)


class VisionAgent:
    """
    👁️ Vision Agent v5.0
    강사의 비언어적 요소(제스처, 시선, 표정)를 분석

    v5.0: MediaPipe Face Mesh(468 landmark) + Pose(33 joints)
    폴백: OpenCV Haar Cascade (MediaPipe 미설치 환경)
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {
            "gesture_threshold": 0.6,
            "face_confidence": 0.5
        }

        self.use_mediapipe = HAS_MEDIAPIPE

        if self.use_mediapipe:
            self._init_mediapipe()
        else:
            self._init_opencv_fallback()

        # 움직임 감지를 위한 이전 프레임
        self.prev_frame = None
        self.prev_gray = None
        self.prev_landmarks = None

        # 분석 결과 저장
        self.results: List[VisionMetrics] = []

    def _init_mediapipe(self):
        """MediaPipe 초기화"""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=0.5
        )

    def _init_opencv_fallback(self):
        """OpenCV 폴백 초기화"""
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

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

        if self.use_mediapipe:
            self._analyze_mediapipe(frame, metrics)
        else:
            self._analyze_opencv(frame, metrics)

        # 공통: 움직임 분석
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self._analyze_motion(gray, metrics)

        self.prev_frame = frame.copy()
        self.prev_gray = gray.copy()

        self.results.append(metrics)
        return metrics

    # ================================================================
    # MediaPipe 분석 (v5.0)
    # ================================================================

    def _analyze_mediapipe(self, frame: np.ndarray, metrics: VisionMetrics):
        """MediaPipe 기반 종합 분석"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]

        # 1. Face Mesh 분석
        face_result = self.face_mesh.process(rgb)
        if face_result.multi_face_landmarks:
            landmarks = face_result.multi_face_landmarks[0]
            metrics.face_detected = True

            # 시선 방향 (홍채 랜드마크 기반)
            self._analyze_gaze_mediapipe(landmarks, w, h, metrics)

            # 표정 활력 (얼굴 랜드마크 변화량)
            self._analyze_expression_mediapipe(landmarks, metrics)

            # 머리 기울기
            self._analyze_head_tilt(landmarks, h, metrics)

            self.prev_landmarks = landmarks

        # 2. Pose 분석
        pose_result = self.pose.process(rgb)
        if pose_result.pose_landmarks:
            pose = pose_result.pose_landmarks
            self._analyze_pose_mediapipe(pose, w, h, metrics)

    def _analyze_gaze_mediapipe(self, landmarks, w, h, metrics: VisionMetrics):
        """홍채 랜드마크 기반 시선 방향 분석"""
        # MediaPipe Face Mesh 홍채 인덱스
        # 왼눈 홍채: 468-472, 오른눈 홍채: 473-477
        try:
            left_iris = landmarks.landmark[468]   # 왼눈 홍채 중심
            right_iris = landmarks.landmark[473]  # 오른눈 홍채 중심
            nose = landmarks.landmark[1]          # 코 끝

            # 홍채 중심 대비 코 위치로 시선 방향 판단
            iris_center_x = (left_iris.x + right_iris.x) / 2
            nose_x = nose.x

            gaze_offset = iris_center_x - nose_x

            if abs(gaze_offset) < 0.015:
                metrics.gaze_direction = "center"
                metrics.eye_contact = True
            elif gaze_offset < -0.015:
                metrics.gaze_direction = "left"
                metrics.eye_contact = False
            else:
                metrics.gaze_direction = "right"
                metrics.eye_contact = False

            # 코가 화면 중앙에 가까우면 정면 응시
            if 0.3 < nose_x < 0.7 and 0.3 < nose.y < 0.7:
                metrics.eye_contact = True

        except (IndexError, AttributeError):
            # 랜드마크 접근 실패 시 기본값 유지
            pass

    def _analyze_expression_mediapipe(self, landmarks, metrics: VisionMetrics):
        """얼굴 랜드마크 변화량으로 표정 활력 측정"""
        if self.prev_landmarks is None:
            metrics.expression_score = 50.0
            return

        try:
            # 주요 얼굴 포인트 변화량 측정 (입, 눈썹, 볼)
            key_indices = [
                61, 291,    # 입 좌우
                0, 17,      # 입 상하
                70, 300,    # 눈썹 좌우
                152, 10,    # 턱, 이마
            ]

            total_movement = 0.0
            for idx in key_indices:
                curr = landmarks.landmark[idx]
                prev = self.prev_landmarks.landmark[idx]
                dx = curr.x - prev.x
                dy = curr.y - prev.y
                total_movement += (dx * dx + dy * dy) ** 0.5

            # 변화량을 0~100 점수로 변환
            metrics.expression_score = min(100, total_movement * 5000)
        except (IndexError, AttributeError):
            metrics.expression_score = 50.0

    def _analyze_head_tilt(self, landmarks, h, metrics: VisionMetrics):
        """머리 기울기 분석"""
        try:
            left_ear = landmarks.landmark[234]
            right_ear = landmarks.landmark[454]

            dy = right_ear.y - left_ear.y
            dx = right_ear.x - left_ear.x

            angle = np.degrees(np.arctan2(dy, dx))
            metrics.head_tilt = round(angle, 1)
        except (IndexError, AttributeError):
            pass

    def _analyze_pose_mediapipe(self, pose, w, h, metrics: VisionMetrics):
        """MediaPipe Pose 기반 제스처/자세 분석"""
        lm = pose.landmark

        # 어깨 각도 (자세 개방성)
        try:
            l_shoulder = lm[11]
            r_shoulder = lm[12]
            shoulder_width = abs(l_shoulder.x - r_shoulder.x)
            metrics.shoulder_angle = shoulder_width
            metrics.body_openness = min(1.0, shoulder_width * 3.0)
        except IndexError:
            pass

        # 손 위치
        try:
            l_wrist = lm[15]
            r_wrist = lm[16]
            l_shoulder = lm[11]
            r_shoulder = lm[12]

            # 손목-어깨 Y좌표 비교
            avg_wrist_y = (l_wrist.y + r_wrist.y) / 2
            avg_shoulder_y = (l_shoulder.y + r_shoulder.y) / 2

            if avg_wrist_y < avg_shoulder_y - 0.1:
                metrics.hand_position = "high"
            elif avg_wrist_y > avg_shoulder_y + 0.2:
                metrics.hand_position = "low"
            else:
                metrics.hand_position = "mid"
        except IndexError:
            pass

        # 팔 제스처 유형 분류
        try:
            l_elbow = lm[13]
            r_elbow = lm[14]
            l_wrist = lm[15]
            r_wrist = lm[16]

            # 팔 벌림 정도
            arm_spread = abs(l_wrist.x - r_wrist.x)
            arm_height = avg_shoulder_y - avg_wrist_y

            if arm_spread > 0.5:
                metrics.arm_gesture_type = "open"
                metrics.gesture_active = True
                metrics.gesture_score = min(100, arm_spread * 150)
            elif arm_height > 0.15:
                metrics.arm_gesture_type = "pointing"
                metrics.gesture_active = True
                metrics.gesture_score = min(100, arm_height * 300)
            elif arm_spread < 0.15:
                metrics.arm_gesture_type = "closed"
                metrics.gesture_active = False
                metrics.gesture_score = 10.0
            else:
                metrics.arm_gesture_type = "none"
                metrics.gesture_active = arm_spread > 0.25
                metrics.gesture_score = min(100, arm_spread * 100)
        except (IndexError, UnboundLocalError):
            pass

    # ================================================================
    # OpenCV 폴백 (v4.x 호환)
    # ================================================================

    def _analyze_opencv(self, frame: np.ndarray, metrics: VisionMetrics):
        """OpenCV 기반 간소화 분석 (MediaPipe 미설치 환경)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        height, width = frame.shape[:2]

        # 얼굴 감지
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30)
        )

        if len(faces) > 0:
            metrics.face_detected = True
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face

            face_center_x = (x + w // 2) / width
            is_centered = 0.3 < face_center_x < 0.7
            metrics.eye_contact = is_centered
            metrics.gaze_direction = "center" if is_centered else ("left" if face_center_x < 0.3 else "right")

            face_size_ratio = (w * h) / (width * height)
            metrics.expression_score = min(100, face_size_ratio * 1000)

        # 영역별 분석
        self._analyze_regions_opencv(frame, metrics)

    def _analyze_regions_opencv(self, frame: np.ndarray, metrics: VisionMetrics):
        """프레임 영역별 분석 (폴백)"""
        height, width = frame.shape[:2]

        top_half = frame[:height//2, :]
        bottom_half = frame[height//2:, :]

        top_edges = cv2.Canny(cv2.cvtColor(top_half, cv2.COLOR_BGR2GRAY), 50, 150)
        bottom_edges = cv2.Canny(cv2.cvtColor(bottom_half, cv2.COLOR_BGR2GRAY), 50, 150)

        top_activity = np.count_nonzero(top_edges) / top_edges.size
        bottom_activity = np.count_nonzero(bottom_edges) / bottom_edges.size

        if top_activity > bottom_activity * 1.5:
            metrics.hand_position = "high"
        elif bottom_activity > top_activity * 1.5:
            metrics.hand_position = "low"
        else:
            metrics.hand_position = "mid"

        metrics.body_openness = min(1.0, (top_activity + bottom_activity) * 10)

    # ================================================================
    # 공통 분석
    # ================================================================

    def _analyze_motion(self, gray: np.ndarray, metrics: VisionMetrics):
        """움직임 분석"""
        if self.prev_gray is None:
            return

        diff = cv2.absdiff(gray, self.prev_gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        motion_pixels = np.count_nonzero(thresh)
        total_pixels = thresh.size
        motion_ratio = motion_pixels / total_pixels

        metrics.motion_score = min(100, motion_ratio * 500)

        # MediaPipe가 제스처를 분석하지 못한 경우 모션 기반 폴백
        if not metrics.gesture_active:
            metrics.gesture_active = motion_ratio > 0.02
            if metrics.gesture_score == 0:
                metrics.gesture_score = metrics.motion_score

    def get_summary(self) -> Dict:
        """분석 결과 요약"""
        if not self.results:
            return {"error": "분석 결과가 없습니다"}

        total = len(self.results)

        summary = {
            "total_frames_analyzed": total,
            "analysis_engine": "mediapipe" if self.use_mediapipe else "opencv",
            "gesture_active_ratio": sum(1 for r in self.results if r.gesture_active) / total,
            "avg_gesture_score": float(np.mean([r.gesture_score for r in self.results])),
            "eye_contact_ratio": sum(1 for r in self.results if r.eye_contact) / total,
            "face_detection_ratio": sum(1 for r in self.results if r.face_detected) / total,
            "avg_expression_score": float(np.mean([r.expression_score for r in self.results])),
            "avg_body_openness": float(np.mean([r.body_openness for r in self.results])),
            "avg_motion_score": float(np.mean([r.motion_score for r in self.results])),
            "hand_position_distribution": self._get_hand_distribution(),
        }

        # v5.0 추가 요약
        if self.use_mediapipe:
            summary["gaze_distribution"] = self._get_gaze_distribution()
            summary["gesture_type_distribution"] = self._get_gesture_type_distribution()
            summary["avg_head_tilt"] = float(np.mean([abs(r.head_tilt) for r in self.results]))

        return summary

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

    def _get_gaze_distribution(self) -> Dict[str, float]:
        """시선 방향 분포 (v5.0)"""
        if not self.results:
            return {}
        gazes = [r.gaze_direction for r in self.results]
        total = len(gazes)
        return {
            "left": gazes.count("left") / total,
            "center": gazes.count("center") / total,
            "right": gazes.count("right") / total,
        }

    def _get_gesture_type_distribution(self) -> Dict[str, float]:
        """제스처 유형 분포 (v5.0)"""
        if not self.results:
            return {}
        types = [r.arm_gesture_type for r in self.results]
        total = len(types)
        return {
            "open": types.count("open") / total,
            "pointing": types.count("pointing") / total,
            "closed": types.count("closed") / total,
            "none": types.count("none") / total,
        }

    def get_timeline(self) -> List[Dict]:
        """시간별 분석 결과"""
        return [
            {
                "timestamp": r.timestamp,
                "gesture_score": r.gesture_score,
                "eye_contact": r.eye_contact,
                "expression_score": r.expression_score,
                "motion_score": r.motion_score,
                "gaze_direction": r.gaze_direction,
                "arm_gesture_type": r.arm_gesture_type,
            }
            for r in self.results
        ]

    def reset(self):
        """분석 결과 초기화"""
        self.results = []
        self.prev_frame = None
        self.prev_gray = None
        self.prev_landmarks = None
