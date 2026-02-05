"""
🎨 Content Agent - 슬라이드/화면 품질 분석
로컬 OCR(pytesseract)과 OpenCV를 활용한 화면 분석 (API 키 불필요)
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# pytesseract는 선택적 import
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


@dataclass
class ContentMetrics:
    """화면/슬라이드 분석 결과"""
    timestamp: float
    text_density: int = 0              # 감지된 텍스트 글자 수
    text_density_score: int = 5        # 텍스트 밀도 점수 (1-10, 10=매우 많음)
    readability: str = "unknown"       # good, bad, unknown
    slide_detected: bool = False       # 슬라이드 영역 감지 여부
    speaker_visible: bool = False      # 강사 영상 감지 여부
    speaker_overlap: bool = False      # 강사가 슬라이드를 가리는지
    color_contrast: float = 0.0        # 색상 대비 (0-1)
    brightness: float = 0.0            # 평균 밝기 (0-255)
    complexity_score: float = 0.0      # 화면 복잡도 (0-100)


class ContentAgent:
    """
    🎨 Content Agent
    PPT/화면 구성, 텍스트 밀도, 가독성 분석
    (Gemini API 없이 로컬 분석)
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {
            "text_density_threshold": 150,
            "min_font_detection": 12,
            "ocr_language": "kor+eng",
        }
        
        self.results: List[ContentMetrics] = []
        
        if not TESSERACT_AVAILABLE:
            print("[!] pytesseract not installed. Text analysis will be limited.")
    
    def analyze_frame(self, frame: np.ndarray, timestamp: float) -> ContentMetrics:
        """
        단일 프레임의 화면 구성 분석
        
        Args:
            frame: BGR 이미지 (OpenCV 형식)
            timestamp: 프레임 타임스탬프 (초)
            
        Returns:
            ContentMetrics 객체
        """
        metrics = ContentMetrics(timestamp=timestamp)
        
        # 1. 기본 이미지 속성 분석
        self._analyze_basic_properties(frame, metrics)
        
        # 2. 화면 영역 분석 (슬라이드 vs 강사)
        self._analyze_regions(frame, metrics)
        
        # 3. 텍스트 분석 (OCR 사용 가능 시)
        if TESSERACT_AVAILABLE:
            self._analyze_text(frame, metrics)
        else:
            self._estimate_text_density(frame, metrics)
        
        # 4. 화면 복잡도 분석
        self._analyze_complexity(frame, metrics)
        
        self.results.append(metrics)
        return metrics
    
    def _analyze_basic_properties(self, frame: np.ndarray, metrics: ContentMetrics):
        """기본 이미지 속성 분석"""
        # 밝기 계산
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        metrics.brightness = float(np.mean(gray))
        
        # 색상 대비 계산
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        metrics.color_contrast = float(np.std(l_channel) / 128)
    
    def _analyze_regions(self, frame: np.ndarray, metrics: ContentMetrics):
        """화면 영역 분석 (슬라이드, 강사 영역 감지)"""
        height, width = frame.shape[:2]
        
        # 프레임을 영역으로 분할하여 분석
        # 일반적인 화면 공유 레이아웃 가정:
        # - 슬라이드: 주로 중앙~오른쪽
        # - 강사: 좌측 하단 또는 우측 상단 작은 영역
        
        # 화면 각 영역의 특성 분석
        regions = {
            "top_left": frame[0:height//3, 0:width//3],
            "top_right": frame[0:height//3, 2*width//3:],
            "bottom_left": frame[2*height//3:, 0:width//3],
            "bottom_right": frame[2*height//3:, 2*width//3:],
            "center": frame[height//4:3*height//4, width//4:3*width//4]
        }
        
        # 얼굴 감지로 강사 영역 확인
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            metrics.speaker_visible = True
            
            # 얼굴이 중앙에 있으면 슬라이드를 가릴 가능성
            for (x, y, w, h) in faces:
                face_center_x = x + w // 2
                if width // 3 < face_center_x < 2 * width // 3:
                    metrics.speaker_overlap = True
                    break
        
        # 슬라이드 감지 (텍스트/도형이 있는 균일한 배경 영역)
        center_region = regions["center"]
        center_gray = cv2.cvtColor(center_region, cv2.COLOR_BGR2GRAY)
        
        # 엣지 감지로 콘텐츠 존재 확인
        edges = cv2.Canny(center_gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # 일정 수준의 엣지 밀도가 있으면 슬라이드로 판단
        if 0.01 < edge_density < 0.3:
            metrics.slide_detected = True
    
    def _analyze_text(self, frame: np.ndarray, metrics: ContentMetrics):
        """OCR을 통한 텍스트 분석"""
        try:
            # 전처리: 텍스트 인식률 향상
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 적응형 이진화
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            # OCR 수행
            text = pytesseract.image_to_string(
                binary, 
                lang=self.config["ocr_language"]
            )
            
            # 텍스트 밀도 계산
            # 공백, 특수문자 제거 후 글자 수
            clean_text = ''.join(c for c in text if c.isalnum())
            metrics.text_density = len(clean_text)
            
            # 텍스트 밀도 점수 (1-10)
            threshold = self.config["text_density_threshold"]
            density_ratio = metrics.text_density / threshold
            metrics.text_density_score = min(10, max(1, int(density_ratio * 5) + 1))
            
            # 가독성 판단
            if metrics.text_density > threshold * 1.5:
                metrics.readability = "bad"  # 텍스트 과다
            elif metrics.text_density < 10:
                metrics.readability = "good"  # 적절하거나 이미지 위주
            else:
                metrics.readability = "good"
                
        except Exception as e:
            print(f"[!] OCR Error: {e}")
            self._estimate_text_density(frame, metrics)
    
    def _estimate_text_density(self, frame: np.ndarray, metrics: ContentMetrics):
        """OCR 없이 텍스트 밀도 추정 (엣지 기반)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 텍스트 영역 감지 (MSER 알고리즘)
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)
        
        # 텍스트로 추정되는 영역 수로 밀도 추정
        estimated_chars = len(regions) // 3  # 대략적인 글자 수 추정
        metrics.text_density = estimated_chars
        
        # 점수 계산
        density_ratio = estimated_chars / self.config["text_density_threshold"]
        metrics.text_density_score = min(10, max(1, int(density_ratio * 5) + 1))
        
        if estimated_chars > self.config["text_density_threshold"]:
            metrics.readability = "bad"
        else:
            metrics.readability = "unknown"
    
    def _analyze_complexity(self, frame: np.ndarray, metrics: ContentMetrics):
        """화면 복잡도 분석"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Laplacian variance로 복잡도 측정
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        # 정규화 (0-100)
        metrics.complexity_score = min(100, variance / 50)
    
    def get_summary(self) -> Dict:
        """분석 결과 요약"""
        if not self.results:
            return {"error": "분석 결과가 없습니다"}
        
        total = len(self.results)
        
        return {
            "total_frames_analyzed": total,
            "avg_text_density": np.mean([r.text_density for r in self.results]),
            "avg_text_density_score": np.mean([r.text_density_score for r in self.results]),
            "high_density_ratio": sum(1 for r in self.results if r.text_density_score >= 7) / total,
            "slide_detection_ratio": sum(1 for r in self.results if r.slide_detected) / total,
            "speaker_visible_ratio": sum(1 for r in self.results if r.speaker_visible) / total,
            "speaker_overlap_ratio": sum(1 for r in self.results if r.speaker_overlap) / total,
            "avg_brightness": np.mean([r.brightness for r in self.results]),
            "avg_complexity": np.mean([r.complexity_score for r in self.results]),
            "warnings": self._get_warnings()
        }
    
    def _get_warnings(self) -> List[str]:
        """경고 메시지 생성"""
        if not self.results:
            return []
        
        warnings = []
        total = len(self.results)
        
        # Calculate values directly to avoid recursion
        high_density_ratio = sum(1 for r in self.results if r.text_density_score >= 7) / total
        speaker_overlap_ratio = sum(1 for r in self.results if r.speaker_overlap) / total
        avg_brightness = np.mean([r.brightness for r in self.results])
        
        if high_density_ratio > 0.3:
            warnings.append("[!] High text density detected in over 30% of frames")
        
        if speaker_overlap_ratio > 0.2:
            warnings.append("[!] Speaker frequently overlaps slide content")
        
        if avg_brightness < 80:
            warnings.append("[!] Screen is generally too dark")
        elif avg_brightness > 220:
            warnings.append("[!] Screen is generally too bright")
        
        return warnings
    
    def get_timeline(self) -> List[Dict]:
        """시간별 분석 결과"""
        return [
            {
                "timestamp": r.timestamp,
                "text_density_score": r.text_density_score,
                "readability": r.readability,
                "slide_detected": r.slide_detected,
                "speaker_overlap": r.speaker_overlap
            }
            for r in self.results
        ]
    
    def find_high_density_frames(self) -> List[float]:
        """텍스트 밀도가 높은 프레임 타임스탬프"""
        return [
            r.timestamp 
            for r in self.results 
            if r.text_density_score >= 7
        ]
    
    def reset(self):
        """분석 결과 초기화"""
        self.results = []
