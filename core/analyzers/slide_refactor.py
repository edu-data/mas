"""
💡 Slide Refactoring Suggestions - PPT 자동 수정 제안
텍스트 과다 슬라이드에 대한 개선 방안 제시
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from pathlib import Path

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


@dataclass
class SlideRefactorSuggestion:
    """슬라이드 수정 제안"""
    timestamp: float
    frame_path: Optional[Path]
    issue_type: str
    severity: str              # low, medium, high
    original_text_count: int
    suggested_text_count: int
    suggestion: str
    action_items: List[str]


class SlideRefactorAnalyzer:
    """
    PPT/슬라이드 자동 수정 제안 분석기
    
    분석 항목:
    1. 텍스트 과다 슬라이드 → 요약 제안
    2. 가독성 문제 → 레이아웃 개선
    3. 시각화 부족 → 차트/이미지 추천
    """
    
    # 텍스트 밀도 기준
    TEXT_THRESHOLDS = {
        "optimal": 50,       # 이상적인 글자 수
        "warning": 100,      # 경고 수준
        "critical": 150      # 심각한 수준
    }
    
    # 개선 템플릿
    REFACTOR_TEMPLATES = {
        "text_overload": {
            "title": "텍스트 과다",
            "suggestion": "슬라이드당 핵심 메시지 3개 이하로 축약하세요",
            "actions": [
                "긴 문장을 키워드로 압축",
                "부가 설명은 노트에 작성",
                "관련 아이콘/이미지 추가"
            ]
        },
        "no_visual": {
            "title": "시각 자료 부족",
            "suggestion": "텍스트만으로 구성된 슬라이드입니다. 시각화를 추가하세요",
            "actions": [
                "핵심 데이터를 차트로 표현",
                "프로세스는 다이어그램으로",
                "관련 이미지 1개 이상 추가"
            ]
        },
        "poor_contrast": {
            "title": "가독성 문제",
            "suggestion": "텍스트와 배경의 대비가 낮습니다",
            "actions": [
                "배경색을 단순화",
                "텍스트 색상 대비 높이기",
                "폰트 크기 24pt 이상 권장"
            ]
        },
        "cluttered": {
            "title": "복잡한 레이아웃",
            "suggestion": "화면에 요소가 너무 많습니다",
            "actions": [
                "하나의 핵심 메시지에 집중",
                "여백(white space) 확보",
                "슬라이드 분할 고려"
            ]
        }
    }
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("./output/refactor_suggestions")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.suggestions: List[SlideRefactorSuggestion] = []
    
    def analyze_frame(
        self,
        frame: np.ndarray,
        timestamp: float,
        content_metrics: Dict
    ) -> Optional[SlideRefactorSuggestion]:
        """
        프레임 분석 후 수정 제안 생성
        
        Args:
            frame: BGR 이미지
            timestamp: 타임스탬프 (초)
            content_metrics: ContentAgent에서 제공한 메트릭
            
        Returns:
            SlideRefactorSuggestion 또는 None
        """
        suggestion = None
        
        text_density = content_metrics.get("text_density", 0)
        text_density_score = content_metrics.get("text_density_score", 5)
        complexity = content_metrics.get("complexity_score", 0)
        brightness = content_metrics.get("brightness", 128)
        
        # 1. 텍스트 과다 체크
        if text_density > self.TEXT_THRESHOLDS["critical"]:
            suggestion = self._create_suggestion(
                frame, timestamp, "text_overload", "high",
                text_density
            )
        elif text_density > self.TEXT_THRESHOLDS["warning"]:
            suggestion = self._create_suggestion(
                frame, timestamp, "text_overload", "medium",
                text_density
            )
        
        # 2. 가독성 문제 체크
        elif brightness < 60 or brightness > 240:
            suggestion = self._create_suggestion(
                frame, timestamp, "poor_contrast", "medium",
                text_density
            )
        
        # 3. 복잡한 레이아웃 체크
        elif complexity > 80:
            suggestion = self._create_suggestion(
                frame, timestamp, "cluttered", "medium",
                text_density
            )
        
        # 4. 시각 자료 부족 (텍스트는 많으나 이미지 영역 없음)
        elif text_density > 80 and complexity < 30:
            suggestion = self._create_suggestion(
                frame, timestamp, "no_visual", "low",
                text_density
            )
        
        if suggestion:
            self.suggestions.append(suggestion)
        
        return suggestion
    
    def _create_suggestion(
        self,
        frame: np.ndarray,
        timestamp: float,
        issue_type: str,
        severity: str,
        text_count: int
    ) -> SlideRefactorSuggestion:
        """수정 제안 생성"""
        template = self.REFACTOR_TEMPLATES.get(issue_type, {})
        
        # 프레임 저장 (선택)
        frame_path = None
        if self.output_dir:
            frame_path = self.output_dir / f"slide_{timestamp:.0f}.jpg"
            cv2.imwrite(str(frame_path), frame)
        
        # 권장 글자 수 계산
        suggested_count = min(
            self.TEXT_THRESHOLDS["optimal"],
            int(text_count * 0.4)  # 60% 축약
        )
        
        return SlideRefactorSuggestion(
            timestamp=timestamp,
            frame_path=frame_path,
            issue_type=issue_type,
            severity=severity,
            original_text_count=text_count,
            suggested_text_count=suggested_count,
            suggestion=template.get("suggestion", ""),
            action_items=template.get("actions", [])
        )
    
    def generate_text_summary(self, frame: np.ndarray) -> Optional[str]:
        """
        OCR로 텍스트 추출 후 요약 생성
        (실제 구현시 LLM API 연동 필요)
        """
        if not TESSERACT_AVAILABLE:
            return None
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, lang="kor+eng")
            
            # 간단한 요약: 첫 50자 + "..."
            if len(text) > 50:
                return text[:50] + "..."
            return text
            
        except Exception:
            return None
    
    def get_refactor_report(self) -> Dict:
        """수정 제안 리포트"""
        if not self.suggestions:
            return {
                "total_issues": 0,
                "message": "슬라이드 수정이 필요한 부분이 없습니다 👍"
            }
        
        by_type = {}
        by_severity = {"low": 0, "medium": 0, "high": 0}
        
        for s in self.suggestions:
            by_type[s.issue_type] = by_type.get(s.issue_type, 0) + 1
            by_severity[s.severity] += 1
        
        return {
            "total_issues": len(self.suggestions),
            "by_type": by_type,
            "by_severity": by_severity,
            "critical_timestamps": [
                s.timestamp for s in self.suggestions 
                if s.severity == "high"
            ],
            "suggestions": [
                {
                    "timestamp": s.timestamp,
                    "issue": self.REFACTOR_TEMPLATES.get(s.issue_type, {}).get("title", s.issue_type),
                    "suggestion": s.suggestion,
                    "actions": s.action_items
                }
                for s in self.suggestions[:10]  # 상위 10개
            ]
        }
    
    def format_suggestion_html(self, suggestion: SlideRefactorSuggestion) -> str:
        """HTML 형식 제안 카드"""
        severity_color = {
            "high": "#ef4444",
            "medium": "#eab308",
            "low": "#22c55e"
        }
        
        actions_html = "".join(
            f"<li>{action}</li>" for action in suggestion.action_items
        )
        
        return f"""
        <div class="refactor-card" style="border-left: 4px solid {severity_color.get(suggestion.severity, '#6b7280')};">
            <div class="time">{self._format_time(suggestion.timestamp)}</div>
            <h4>{self.REFACTOR_TEMPLATES.get(suggestion.issue_type, {}).get('title', suggestion.issue_type)}</h4>
            <p>{suggestion.suggestion}</p>
            <ul>{actions_html}</ul>
            <div class="stats">
                현재 글자 수: {suggestion.original_text_count} → 권장: {suggestion.suggested_text_count}
            </div>
        </div>
        """
    
    def _format_time(self, seconds: float) -> str:
        """초를 MM:SS 형식으로"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
    
    def reset(self):
        """분석 결과 초기화"""
        self.suggestions = []
