"""
👁️ Vision Agent - 강사 비언어 행동 분석
v6.0: MediaPipe Tasks API (FaceLandmarker + PoseLandmarker) 마이그레이션
     mp.solutions 제거 → mp.tasks.vision 사용
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

# MediaPipe Tasks API (v0.10+)
try:
    import mediapipe as mp
    _MP_VIS = mp.tasks.vision
    _BASE_OPTS = mp.tasks.BaseOptions
    _MODEL_DIR = Path(mp.__file__).parent / "models"
    HAS_MEDIAPIPE = (_MODEL_DIR / "face_landmarker.task").exists()
except (ImportError, AttributeError):
    HAS_MEDIAPIPE = False


@dataclass
class VisionMetrics:
    """비전 분석 결과 메트릭"""
    timestamp: float
    gesture_active: bool = False
    gesture_score: float = 0.0
    hand_position: str = "unknown"
    eye_contact: bool = False
    face_detected: bool = False
    expression_score: float = 50.0
    body_openness: float = 0.5
    motion_score: float = 0.0
    gaze_direction: str = "center"
    shoulder_angle: float = 0.0
    arm_gesture_type: str = "none"
    head_tilt: float = 0.0


class VisionAgent:
    """
    👁️ Vision Agent v6.0
    강사의 비언어적 요소(제스처, 시선, 표정)를 분석

    v6.0: MediaPipe Tasks API (FaceLandmarker + PoseLandmarker)
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
        """MediaPipe Tasks API 초기화"""
        face_model = str(_MODEL_DIR / "face_landmarker.task")
        pose_model = str(_MODEL_DIR / "pose_landmarker_lite.task")

        # FaceLandmarker 생성
        face_opts = _MP_VIS.FaceLandmarkerOptions(
            base_options=_BASE_OPTS(model_asset_path=face_model),
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_face_blendshapes=True,
        )
        self.face_landmarker = _MP_VIS.FaceLandmarker.create_from_options(face_opts)

        # PoseLandmarker 생성
        pose_opts = _MP_VIS.PoseLandmarkerOptions(
            base_options=_BASE_OPTS(model_asset_path=pose_model),
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.pose_landmarker = _MP_VIS.PoseLandmarker.create_from_options(pose_opts)

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
    # MediaPipe Tasks 분석
    # ================================================================
    def _analyze_mediapipe(self, frame: np.ndarray, metrics: VisionMetrics):
        """MediaPipe Tasks API 기반 종합 분석"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        h, w = frame.shape[:2]

        # 얼굴 랜드마크 분석
        try:
            face_result = self.face_landmarker.detect(mp_image)
            if face_result.face_landmarks:
                metrics.face_detected = True
                lm = face_result.face_landmarks[0]  # 첫 번째 얼굴
                self._analyze_gaze(lm, w, h, metrics)
                self._analyze_expression(face_result, metrics)
                self._analyze_head_tilt(lm, h, metrics)
        except Exception:
            pass

        # 자세/제스처 분석
        try:
            pose_result = self.pose_landmarker.detect(mp_image)
            if pose_result.pose_landmarks:
                pose_lm = pose_result.pose_landmarks[0]
                self._analyze_pose(pose_lm, w, h, metrics)
        except Exception:
            pass

    def _analyze_gaze(self, landmarks, w, h, metrics: VisionMetrics):
        """랜드마크 기반 시선 방향 분석"""
        # 코 끝 (landmark 1) 기준 시선 추정
        nose = landmarks[1]
        nose_x = nose.x

        # 왼쪽 눈 (landmark 33), 오른쪽 눈 (landmark 263)
        left_eye = landmarks[33]
        right_eye = landmarks[263]

        eye_center_x = (left_eye.x + right_eye.x) / 2
        eye_center_y = (left_eye.y + right_eye.y) / 2

        # 시선 방향 판별
        x_offset = nose_x - eye_center_x
        if abs(x_offset) < 0.02:
            metrics.gaze_direction = "center"
            metrics.eye_contact = True
        elif x_offset > 0.02:
            metrics.gaze_direction = "right"
            metrics.eye_contact = False
        else:
            metrics.gaze_direction = "left"
            metrics.eye_contact = False

        # 약간의 좌우 움직임도 학생 시선 접촉으로 간주 (±3도 범위)
        if abs(x_offset) < 0.04 and abs(eye_center_y - 0.35) < 0.15:
            metrics.eye_contact = True

    def _analyze_expression(self, face_result, metrics: VisionMetrics):
        """Blendshape 기반 표정 분석"""
        if face_result.face_blendshapes:
            blendshapes = face_result.face_blendshapes[0]
            bs_dict = {bs.category_name: bs.score for bs in blendshapes}

            # 미소 정도
            smile = max(bs_dict.get('mouthSmileLeft', 0), bs_dict.get('mouthSmileRight', 0))
            # 눈 크기 (openness)
            eye_open = (bs_dict.get('eyeBlinkLeft', 0) + bs_dict.get('eyeBlinkRight', 0)) / 2
            # 입 열림 (말하기)
            mouth_open = bs_dict.get('jawOpen', 0)
            # 눈썹 올림 (강조)
            brow_up = max(bs_dict.get('browOuterUpLeft', 0), bs_dict.get('browOuterUpRight', 0))

            # 표정 점수 (0-100)
            # 미소 + 말하기 활동 + 눈썹 표현 → 높은 점수
            expression = 50.0
            expression += smile * 30  # 미소 → +30까지
            expression += mouth_open * 15  # 말하기 → +15까지
            expression += brow_up * 10  # 강조 → +10까지
            expression -= eye_open * 20  # 눈 감기 → -20까지

            metrics.expression_score = max(0, min(100, expression))

    def _analyze_head_tilt(self, landmarks, h, metrics: VisionMetrics):
        """머리 기울기 분석"""
        # 왼쪽 귀 (127), 오른쪽 귀 (356)
        left_ear = landmarks[127]
        right_ear = landmarks[356]

        dy = (right_ear.y - left_ear.y) * h
        dx = (right_ear.x - left_ear.x) * h
        if dx != 0:
            metrics.head_tilt = np.degrees(np.arctan2(dy, dx))

    def _analyze_pose(self, pose_lm, w, h, metrics: VisionMetrics):
        """MediaPipe Pose 기반 제스처/자세 분석"""
        # 주요 랜드마크 좌표
        # 11: 왼쪽 어깨, 12: 오른쪽 어깨
        # 13: 왼쪽 팔꿈치, 14: 오른쪽 팔꿈치
        # 15: 왼쪽 손목, 16: 오른쪽 손목
        # 23: 왼쪽 엉덩이, 24: 오른쪽 엉덩이

        left_shoulder = pose_lm[11]
        right_shoulder = pose_lm[12]
        left_elbow = pose_lm[13]
        right_elbow = pose_lm[14]
        left_wrist = pose_lm[15]
        right_wrist = pose_lm[16]

        # 1. 어깨 각도 (body openness)
        shoulder_width = abs(right_shoulder.x - left_shoulder.x) * w
        shoulder_center_y = (left_shoulder.y + right_shoulder.y) / 2

        # 2. 손 위치 판별
        hand_y_avg = (left_wrist.y + right_wrist.y) / 2
        shoulder_y = shoulder_center_y

        if hand_y_avg < shoulder_y - 0.1:
            metrics.hand_position = "above_shoulder"
            metrics.gesture_active = True
            metrics.gesture_score = 0.9
        elif hand_y_avg < shoulder_y + 0.05:
            metrics.hand_position = "shoulder_level"
            metrics.gesture_active = True
            metrics.gesture_score = 0.7
        elif hand_y_avg < shoulder_y + 0.2:
            metrics.hand_position = "chest_level"
            metrics.gesture_active = True
            metrics.gesture_score = 0.5
        else:
            metrics.hand_position = "waist_or_below"
            metrics.gesture_active = False
            metrics.gesture_score = 0.1

        # 3. 양팔 벌림 (body openness)
        left_arm_spread = abs(left_wrist.x - left_shoulder.x) * w
        right_arm_spread = abs(right_wrist.x - right_shoulder.x) * w
        arm_spread = (left_arm_spread + right_arm_spread) / 2

        if arm_spread > shoulder_width * 0.8:
            metrics.body_openness = 0.9
        elif arm_spread > shoulder_width * 0.5:
            metrics.body_openness = 0.7
        elif arm_spread > shoulder_width * 0.3:
            metrics.body_openness = 0.5
        else:
            metrics.body_openness = 0.3

        # 4. 어깨 기울기
        dy = (right_shoulder.y - left_shoulder.y) * h
        dx = (right_shoulder.x - left_shoulder.x) * w
        if dx != 0:
            metrics.shoulder_angle = np.degrees(np.arctan2(dy, dx))

        # 5. 제스처 유형 판별
        left_elbow_angle = self._calc_angle(left_shoulder, left_elbow, left_wrist)
        right_elbow_angle = self._calc_angle(right_shoulder, right_elbow, right_wrist)

        if metrics.hand_position == "above_shoulder":
            metrics.arm_gesture_type = "pointing_up"
        elif left_elbow_angle < 90 or right_elbow_angle < 90:
            metrics.arm_gesture_type = "bent_active"
        elif left_elbow_angle > 150 and right_elbow_angle > 150:
            metrics.arm_gesture_type = "extended"
        else:
            metrics.arm_gesture_type = "relaxed"

    def _calc_angle(self, a, b, c):
        """세 포인트로 각도 계산"""
        ba = np.array([a.x - b.x, a.y - b.y])
        bc = np.array([c.x - b.x, c.y - b.y])
        cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
        return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))

    # ================================================================
    # OpenCV 폴백 분석
    # ================================================================
    def _analyze_opencv(self, frame: np.ndarray, metrics: VisionMetrics):
        """OpenCV 기반 간소화 분석 (MediaPipe 미설치 환경)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) > 0:
            metrics.face_detected = True
            x, y, fw, fh = faces[0]
            face_center_x = x + fw / 2
            if abs(face_center_x - w / 2) < w * 0.15:
                metrics.eye_contact = True
                metrics.gaze_direction = "center"

            face_roi = gray[y:y+fh, x:x+fw]
            std = np.std(face_roi)
            metrics.expression_score = min(100, 40 + std * 0.8)

        self._analyze_regions_opencv(frame, metrics)

    def _analyze_regions_opencv(self, frame: np.ndarray, metrics: VisionMetrics):
        """프레임 영역별 분석 (폴백)"""
        h, w = frame.shape[:2]

        upper = frame[:h//3, :]
        upper_gray = cv2.cvtColor(upper, cv2.COLOR_BGR2GRAY)
        upper_motion = np.std(upper_gray)

        if upper_motion > 40:
            metrics.gesture_active = True
            metrics.gesture_score = min(1.0, upper_motion / 80)
            metrics.hand_position = "above_shoulder"
        elif upper_motion > 25:
            metrics.gesture_active = True
            metrics.gesture_score = 0.4
            metrics.hand_position = "chest_level"

        # 전체 밝기 변화 → 체형 개방도 추정
        center = frame[h//4:3*h//4, w//4:3*w//4]
        metrics.body_openness = min(1.0, np.std(cv2.cvtColor(center, cv2.COLOR_BGR2GRAY)) / 60)

    # ================================================================
    # 공통 분석
    # ================================================================
    def _analyze_motion(self, gray: np.ndarray, metrics: VisionMetrics):
        """움직임 분석"""
        if self.prev_gray is not None:
            diff = cv2.absdiff(gray, self.prev_gray)
            motion = np.mean(diff)
            metrics.motion_score = float(motion)
        else:
            metrics.motion_score = 0.0

    # ================================================================
    # 요약 및 타임라인
    # ================================================================
    def get_summary(self) -> Dict:
        """분석 결과 요약"""
        if not self.results:
            return {"error": "분석 결과가 없습니다"}

        total = len(self.results)

        summary = {
            "total_frames_analyzed": total,
            "analysis_engine": "mediapipe_tasks" if self.use_mediapipe else "opencv",
            "gesture_active_ratio": sum(1 for r in self.results if r.gesture_active) / total,
            "avg_gesture_score": float(np.mean([r.gesture_score for r in self.results])),
            "eye_contact_ratio": sum(1 for r in self.results if r.eye_contact) / total,
            "face_detection_ratio": sum(1 for r in self.results if r.face_detected) / total,
            "avg_expression_score": float(np.mean([r.expression_score for r in self.results])),
            "avg_body_openness": float(np.mean([r.body_openness for r in self.results])),
            "avg_motion_score": float(np.mean([r.motion_score for r in self.results])),
            "hand_position_distribution": self._get_hand_distribution(),
        }

        # v6.0 추가 요약
        if self.use_mediapipe:
            summary["gaze_distribution"] = self._get_gaze_distribution()
            summary["gesture_type_distribution"] = self._get_gesture_type_distribution()
            summary["avg_head_tilt"] = float(np.mean([abs(r.head_tilt) for r in self.results]))

        return summary

    def _get_hand_distribution(self) -> Dict:
        """손 위치 분포"""
        dist = {}
        total = len(self.results) or 1
        for r in self.results:
            dist[r.hand_position] = dist.get(r.hand_position, 0) + 1
        return {k: round(v / total, 3) for k, v in dist.items()}

    def _get_gaze_distribution(self) -> Dict:
        """시선 방향 분포 (v6.0)"""
        dist = {}
        total = len(self.results) or 1
        for r in self.results:
            dist[r.gaze_direction] = dist.get(r.gaze_direction, 0) + 1
        return {k: round(v / total, 3) for k, v in dist.items()}

    def _get_gesture_type_distribution(self) -> Dict:
        """제스처 유형 분포 (v6.0)"""
        dist = {}
        total = len(self.results) or 1
        for r in self.results:
            dist[r.arm_gesture_type] = dist.get(r.arm_gesture_type, 0) + 1
        return {k: round(v / total, 3) for k, v in dist.items()}

    def get_timeline(self) -> List[Dict]:
        """시간별 분석 결과"""
        return [
            {
                "timestamp": r.timestamp,
                "gesture_active": r.gesture_active,
                "gesture_score": round(r.gesture_score, 2),
                "eye_contact": r.eye_contact,
                "expression_score": round(r.expression_score, 1),
                "body_openness": round(r.body_openness, 2),
                "motion_score": round(r.motion_score, 1),
                "gaze_direction": r.gaze_direction,
                "arm_gesture_type": r.arm_gesture_type,
            }
            for r in self.results
        ]

    def reset(self):
        """분석 결과 초기화"""
        self.results.clear()
        self.prev_frame = None
        self.prev_gray = None
        self.prev_landmarks = None
