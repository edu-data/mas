"""
⚡ Parallel Frame Analyzer - 멀티프로세싱 프레임 분석
CPU 코어를 활용한 병렬 처리로 분석 시간 단축
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import warnings

warnings.filterwarnings("ignore")


@dataclass
class FrameResult:
    """프레임 분석 결과"""
    timestamp: float
    vision_metrics: Dict
    content_metrics: Dict


def analyze_single_frame(args: Tuple) -> Dict:
    """
    단일 프레임 분석 (프로세스 워커에서 실행)
    
    Args:
        args: (frame_bytes, timestamp, frame_shape, config)
    """
    frame_bytes, timestamp, frame_shape, config = args
    
    # 바이트를 numpy array로 복원
    frame = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(frame_shape)
    
    result = {
        "timestamp": timestamp,
        "vision": {},
        "content": {}
    }
    
    try:
        # Vision 분석
        result["vision"] = _analyze_vision(frame, timestamp, config.get("vision", {}))
        
        # Content 분석
        result["content"] = _analyze_content(frame, timestamp, config.get("content", {}))
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def _analyze_vision(frame: np.ndarray, timestamp: float, config: Dict) -> Dict:
    """Vision 분석 (워커 내부)"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    height, width = frame.shape[:2]
    
    # 얼굴 감지
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
    
    face_detected = len(faces) > 0
    eye_contact = False
    expression_score = 50.0
    
    if face_detected:
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face_center_x = (x + w // 2) / width
        eye_contact = 0.3 < face_center_x < 0.7
        face_size_ratio = (w * h) / (width * height)
        expression_score = min(100, face_size_ratio * 1000)
    
    # 움직임 분석은 단일 프레임에서 불가능하므로 기본값
    return {
        "timestamp": timestamp,
        "face_detected": face_detected,
        "eye_contact": eye_contact,
        "expression_score": expression_score,
        "gesture_score": 0.0,
        "motion_score": 0.0
    }


def _analyze_content(frame: np.ndarray, timestamp: float, config: Dict) -> Dict:
    """Content 분석 (워커 내부)"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    height, width = frame.shape[:2]
    
    # 밝기
    brightness = float(np.mean(gray))
    
    # 색상 대비
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]
    color_contrast = float(np.std(l_channel) / 128)
    
    # 텍스트 밀도 추정 (MSER)
    mser = cv2.MSER_create()
    regions, _ = mser.detectRegions(gray)
    estimated_chars = len(regions) // 3
    
    threshold = config.get("text_density_threshold", 150)
    density_ratio = estimated_chars / threshold
    text_density_score = min(10, max(1, int(density_ratio * 5) + 1))
    
    # 복잡도
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    complexity_score = min(100, float(laplacian.var()) / 50)
    
    # 슬라이드 감지
    center = frame[height//4:3*height//4, width//4:3*width//4]
    center_gray = cv2.cvtColor(center, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(center_gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    slide_detected = 0.01 < edge_density < 0.3
    
    return {
        "timestamp": timestamp,
        "text_density": estimated_chars,
        "text_density_score": text_density_score,
        "brightness": brightness,
        "complexity_score": complexity_score,
        "slide_detected": slide_detected,
        "speaker_visible": False,
        "speaker_overlap": False
    }


class ParallelFrameAnalyzer:
    """
    ⚡ 병렬 프레임 분석기
    
    CPU 코어 수에 맞게 프로세스 풀을 생성하고
    프레임들을 병렬로 분석
    """
    
    def __init__(self, max_workers: int = None, config: Dict = None):
        """
        Args:
            max_workers: 워커 수 (None이면 CPU 코어 수 - 1)
            config: Vision/Content 설정
        """
        self.max_workers = max_workers or max(1, cpu_count() - 1)
        self.config = config or {}
        
        print(f"⚡ 병렬 분석기 초기화 (워커: {self.max_workers}개)")
    
    def analyze_frames(
        self,
        frames: List[Tuple[np.ndarray, float]],
        show_progress: bool = True
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        프레임 리스트 병렬 분석
        
        Args:
            frames: [(frame, timestamp), ...] 리스트
            show_progress: 진행률 표시 여부
            
        Returns:
            (vision_results, content_results) 튜플
        """
        if not frames:
            return [], []
        
        total = len(frames)
        print(f"⚡ 병렬 분석 시작: {total}개 프레임, {self.max_workers}개 워커")
        
        # 프레임을 직렬화 가능한 형태로 변환
        tasks = []
        for frame, timestamp in frames:
            frame_bytes = frame.tobytes()
            frame_shape = frame.shape
            tasks.append((frame_bytes, timestamp, frame_shape, self.config))
        
        vision_results = []
        content_results = []
        
        # 병렬 처리
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(analyze_single_frame, task): i 
                for i, task in enumerate(tasks)
            }
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                
                if show_progress and completed % 100 == 0:
                    pct = (completed / total) * 100
                    print(f"   ⚡ 진행: {completed}/{total} ({pct:.1f}%)")
                
                try:
                    result = future.result()
                    vision_results.append(result["vision"])
                    content_results.append(result["content"])
                except Exception as e:
                    print(f"   [!] 프레임 분석 오류: {e}")
        
        # 타임스탬프 순으로 정렬
        vision_results.sort(key=lambda x: x.get("timestamp", 0))
        content_results.sort(key=lambda x: x.get("timestamp", 0))
        
        print(f"✅ 병렬 분석 완료: {len(vision_results)}개")
        
        return vision_results, content_results
    
    def analyze_video(
        self,
        video_path: Path,
        sample_rate: float = 1.0
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        비디오 파일 직접 분석
        
        Args:
            video_path: 비디오 파일 경로
            sample_rate: 초당 샘플링 프레임 수
            
        Returns:
            (vision_results, content_results)
        """
        video_path = Path(video_path)
        cap = cv2.VideoCapture(str(video_path))
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        frame_interval = int(fps / sample_rate)
        
        print(f"🎬 비디오 로드: {video_path.name}")
        print(f"   FPS: {fps:.1f}, 길이: {duration:.1f}초, 샘플링: {sample_rate}/초")
        
        # 먼저 모든 프레임 추출 (메모리에 로드)
        frames = []
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / fps
                frames.append((frame.copy(), timestamp))
            
            frame_idx += 1
        
        cap.release()
        print(f"   프레임 추출 완료: {len(frames)}개")
        
        # 병렬 분석
        return self.analyze_frames(frames)


# 편의 함수
def parallel_analyze(
    video_path: Path,
    sample_rate: float = 1.0,
    max_workers: int = None,
    config: Dict = None
) -> Tuple[List[Dict], List[Dict]]:
    """
    비디오 병렬 분석 편의 함수
    
    Args:
        video_path: 비디오 파일 경로
        sample_rate: 초당 프레임 샘플링
        max_workers: 워커 수
        config: 설정
        
    Returns:
        (vision_results, content_results)
    """
    analyzer = ParallelFrameAnalyzer(max_workers=max_workers, config=config)
    return analyzer.analyze_video(video_path, sample_rate)


if __name__ == "__main__":
    # 테스트
    import time
    
    video = Path(r"D:\data science\02.21\녹화_2025_02_21_08_37_50_910.mp4")
    
    start = time.time()
    vision, content = parallel_analyze(video, sample_rate=1.0)
    elapsed = time.time() - start
    
    print(f"\n분석 시간: {elapsed:.1f}초")
    print(f"Vision 결과: {len(vision)}개")
    print(f"Content 결과: {len(content)}개")
