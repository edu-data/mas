# Analyzers Package
from .incongruence import IncongruenceDetector
from .engagement import EngagementAnalyzer
from .slide_refactor import SlideRefactorAnalyzer
from .timelapse_analyzer import TimeLapseAnalyzer, run_turbo_analysis

# 텍스트 분석 (선택적 - openai-whisper 필요)
try:
    from .text_analyzer import analyze_text_track, TextAnalysisResult
    TEXT_ANALYZER_AVAILABLE = True
except ImportError:
    TEXT_ANALYZER_AVAILABLE = False

__all__ = [
    "IncongruenceDetector",
    "EngagementAnalyzer",
    "SlideRefactorAnalyzer",
    "TimeLapseAnalyzer",
    "run_turbo_analysis",
    "analyze_text_track",
    "TextAnalysisResult"
]
