"""
📚 Pedagogy Agent - 교육학 이론 기반 평가 전문 에이전트
RAG 지식 기반과 연동하여 7차원 교육학 평가를 수행합니다.
"""

from typing import Dict, List
from dataclasses import dataclass, field

DIMENSION_FRAMEWORK = {
    "수업 전문성": {"weight": 20, "theory": "구성주의 학습이론 - 학습 목표의 명확한 제시는 학생의 인지적 스캐폴딩을 제공합니다."},
    "교수학습 방법": {"weight": 20, "theory": "다중지능이론(Gardner) - 다양한 교수법은 학생의 서로 다른 지능 유형에 호소합니다."},
    "판서 및 언어": {"weight": 15, "theory": "이중부호화이론(Paivio) - 시각적, 언어적 정보의 병행 제시가 학습 효과를 높입니다."},
    "수업 태도": {"weight": 15, "theory": "사회학습이론(Bandura) - 교사의 열정적 태도는 학생의 학습 동기에 모델링 효과를 줍니다."},
    "학생 참여": {"weight": 15, "theory": "ZPD(Vygotsky) - 적절한 발문은 학생의 근접발달영역에서의 학습을 촉진합니다."},
    "시간 배분": {"weight": 10, "theory": "ARCS 모델(Keller) - 적절한 시간 배분은 학습자의 주의를 효과적으로 유지합니다."},
    "창의성": {"weight": 5, "theory": "창의적 문제해결(Torrance) - 독창적 수업 설계는 학생의 확산적 사고를 자극합니다."},
}

@dataclass
class DimensionScore:
    name: str; score: float; max_score: float; percentage: float; grade: str
    feedback: str; theory_reference: str; improvement_tips: List[str] = field(default_factory=list)
    def to_dict(self) -> Dict:
        return {"name": self.name, "score": round(self.score, 1), "max_score": self.max_score,
                "percentage": round(self.percentage, 1), "grade": self.grade, "feedback": self.feedback,
                "theory_reference": self.theory_reference, "improvement_tips": self.improvement_tips}

class PedagogyAgent:
    """📚 교육학 이론 기반 7차원 평가 에이전트"""

    def __init__(self, use_rag: bool = True):
        self.use_rag = use_rag
        self._rag_kb = None

    def evaluate(self, vision_summary: Dict, content_summary: Dict, vibe_summary: Dict, stt_result: Dict = None) -> Dict:
        stt = stt_result or {}
        dimensions = [
            self._eval_expertise(content_summary, stt),
            self._eval_methods(content_summary, vision_summary),
            self._eval_language(content_summary, stt, vibe_summary),
            self._eval_attitude(vision_summary, vibe_summary),
            self._eval_participation(stt, vibe_summary),
            self._eval_time(vibe_summary),
            self._eval_creativity(content_summary, vision_summary),
        ]
        total = sum(d.score for d in dimensions)
        return {"total_score": round(total, 1), "grade": self._grade(total),
                "dimensions": [d.to_dict() for d in dimensions],
                "dimension_scores": {d.name: d.score for d in dimensions},
                "theory_references": [d.theory_reference for d in dimensions]}

    def _make_score(self, name, base, dim_key, feedback_fn, tips=None):
        w = DIMENSION_FRAMEWORK[name]["weight"]
        score = min(w, base); pct = (score / w) * 100
        g = "우수" if pct >= 85 else ("양호" if pct >= 70 else ("보통" if pct >= 60 else "노력 필요"))
        return DimensionScore(name=name, score=score, max_score=w, percentage=pct, grade=g,
                              feedback=feedback_fn(pct), theory_reference=DIMENSION_FRAMEWORK[name]["theory"],
                              improvement_tips=tips or [])

    def _eval_expertise(self, content, stt):
        base = 14.0
        if content.get("slide_detected_ratio", 0) > 0.5: base += 2.0
        wc = stt.get("word_count", 0)
        base += 2.0 if wc > 1000 else (1.0 if wc > 500 else 0)
        rate = stt.get("speaking_rate", 125)
        base += 2.0 if 100 <= rate <= 150 else (1.0 if 80 <= rate <= 170 else 0)
        tips = ["학습 목표를 수업 시작 시 명시적으로 제시하세요.", "핵심 개념을 시각적 자료와 함께 구조화하세요."] if min(20, base) < 16 else []
        return self._make_score("수업 전문성", base, "수업 전문성",
            lambda p: "학습 목표가 명확하고 내용 구조화가 체계적입니다." if p >= 85 else
                      ("전반적인 수업 구조가 양호합니다." if p >= 70 else "학습 목표를 명확히 제시하세요."), tips)

    def _eval_methods(self, content, vision):
        base = 13.0
        if content.get("slide_detected_ratio", 0) > 0.3: base += 2.0
        if content.get("avg_color_contrast", 0) > 50: base += 1.5
        g = vision.get("gesture_active_ratio", 0)
        base += 2.0 if g > 0.4 else (1.0 if g > 0.2 else 0)
        if vision.get("avg_motion_score", 0) > 20: base += 1.5
        tips = ["다양한 교수학습 매체를 활용하세요.", "학생 활동 중심의 수업 전략을 포함하세요."] if min(20, base) < 16 else []
        return self._make_score("교수학습 방법", base, "교수학습 방법",
            lambda p: "다양한 교수학습 방법을 효과적으로 활용하고 있습니다." if p >= 85 else
                      ("교수법이 양호합니다." if p >= 70 else "다양한 교수학습 전략을 시도하세요."), tips)

    def _eval_language(self, content, stt, vibe):
        base = 10.0
        if content.get("avg_readability", "") == "good": base += 2.0
        fr = stt.get("filler_ratio", 0.03)
        base += 2.0 if fr < 0.02 else (1.0 if fr < 0.05 else 0)
        if vibe.get("monotone_ratio", 0.5) < 0.3: base += 1.0
        tips = []
        if fr > 0.05: tips.append(f"습관어를 줄이세요 (현재: {fr:.1%}).")
        if min(15, base) < 12: tips.append("판서를 간결하게 정리하세요.")
        return self._make_score("판서 및 언어", base, "판서 및 언어",
            lambda p: "언어 표현이 명확합니다." if p >= 85 else
                      ("양호하나 습관어를 줄이세요." if p >= 70 else "핵심 용어를 정확히 사용하세요."), tips)

    def _eval_attitude(self, vision, vibe):
        base = 10.0
        ec = vision.get("eye_contact_ratio", 0)
        base += 2.0 if ec > 0.6 else (1.0 if ec > 0.3 else 0)
        if vision.get("avg_expression_score", 50) > 60: base += 1.5
        if vibe.get("energy_distribution", {}).get("high", 0) > 0.3: base += 1.5
        tips = []
        if ec < 0.4: tips.append("학생들과 시선을 고르게 맞추세요.")
        if min(15, base) < 12: tips.append("밝은 표정으로 열정을 표현하세요.")
        return self._make_score("수업 태도", base, "수업 태도",
            lambda p: "열정적인 태도와 시선 접촉이 우수합니다." if p >= 85 else
                      ("양호한 태도입니다." if p >= 70 else "적극적인 태도로 열정을 전달하세요."), tips)

    def _eval_participation(self, stt, vibe):
        base = 10.0
        sr = vibe.get("avg_silence_ratio", 0.3)
        base += 2.0 if 0.15 <= sr <= 0.35 else (1.0 if sr > 0.35 else 0)
        pat = stt.get("speaking_pattern", "")
        base += 2.0 if "Conversational" in pat else (1.0 if "Lecture" in pat else 0)
        if stt.get("filler_ratio", 0.03) < 0.02: base += 1.0
        tips = ["개방형 질문으로 학생 사고를 자극하세요.", "구체적 피드백을 제공하세요."] if min(15, base) < 12 else []
        return self._make_score("학생 참여", base, "학생 참여",
            lambda p: "학생 참여를 효과적으로 이끌어내고 있습니다." if p >= 85 else
                      ("참여 유도가 양호합니다." if p >= 70 else "발문 수준을 다양화하세요."), tips)

    def _eval_time(self, vibe):
        base = 7.0
        ed = vibe.get("energy_distribution", {})
        lvs = [ed.get("low", 0), ed.get("normal", 0), ed.get("high", 0)]
        if sum(lvs) > 0:
            base += 2.0 if max(lvs) - min(lvs) < 0.4 else (1.0 if max(lvs) - min(lvs) < 0.6 else 0)
        if vibe.get("monotone_ratio", 0.5) < 0.3: base += 1.0
        tips = ["도입(10%)-전개(70%)-정리(20%) 비율로 시간을 배분하세요."] if min(10, base) < 8 else []
        return self._make_score("시간 배분", base, "시간 배분",
            lambda p: "시간 배분이 적절합니다." if p >= 85 else
                      ("양호하나 정리 단계를 확보하세요." if p >= 70 else "시간 배분을 사전에 계획하세요."), tips)

    def _eval_creativity(self, content, vision):
        base = 3.0
        if content.get("slide_detected_ratio", 0) > 0.5: base += 0.5
        if content.get("avg_color_contrast", 0) > 60: base += 0.5
        if vision.get("avg_motion_score", 0) > 25: base += 0.5
        if vision.get("avg_body_openness", 0.5) > 0.6: base += 0.5
        tips = ["ICT 도구를 활용한 창의적 수업 설계를 시도하세요."] if min(5, base) < 4 else []
        return self._make_score("창의성", base, "창의성",
            lambda p: "창의적인 수업 설계가 돋보입니다." if p >= 85 else
                      ("양호한 수준입니다." if p >= 70 else "독창적인 활동을 시도하세요."), tips)

    def _grade(self, total):
        if total >= 90: return "A"
        elif total >= 85: return "A-"
        elif total >= 80: return "B+"
        elif total >= 75: return "B"
        elif total >= 70: return "B-"
        elif total >= 65: return "C+"
        elif total >= 60: return "C"
        else: return "D"
