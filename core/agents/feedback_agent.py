"""
💡 Feedback Agent - 맞춤형 피드백 생성 전문 에이전트
모든 에이전트 결과를 종합하여 실행 가능한 피드백을 생성합니다.
"""

import os
from typing import Dict, List, Optional

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class FeedbackAgent:
    """
    💡 Feedback Agent
    모든 분석 에이전트의 결과를 종합하여 구체적이고 실행 가능한
    수업 개선 피드백을 생성합니다.

    지원 모드:
    1. Gemini LLM 기반 (API 키 필요)
    2. 규칙 기반 (폴백)
    """

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm and HAS_GENAI
        self._model = None

    def generate(
        self,
        pedagogy_result: Dict,
        vision_summary: Dict = None,
        content_summary: Dict = None,
        vibe_summary: Dict = None,
        stt_result: Dict = None,
    ) -> Dict:
        """
        종합 피드백 생성

        Returns:
            strengths, improvements, action_plan, overall_summary
        """
        vision = vision_summary or {}
        content = content_summary or {}
        vibe = vibe_summary or {}
        stt = stt_result or {}

        # 강점 분석
        strengths = self._identify_strengths(pedagogy_result, vision, vibe, stt)

        # 개선점 분석
        improvements = self._identify_improvements(pedagogy_result, vision, vibe, stt)

        # 실행 계획 생성
        action_plan = self._create_action_plan(improvements)

        # 종합 요약 (LLM 시도 → 규칙 기반 폴백)
        if self.use_llm:
            overall = self._generate_llm_summary(pedagogy_result, strengths, improvements)
        else:
            overall = self._generate_rule_summary(pedagogy_result, strengths, improvements)

        return {
            "strengths": strengths,
            "improvements": improvements,
            "action_plan": action_plan,
            "overall_summary": overall,
            "total_score": pedagogy_result.get("total_score", 0),
            "grade": pedagogy_result.get("grade", "N/A"),
            "method": "llm" if self.use_llm else "rule_based",
        }

    def _identify_strengths(self, ped: Dict, vision: Dict, vibe: Dict, stt: Dict) -> List[Dict]:
        """강점 식별"""
        strengths = []
        dims = ped.get("dimensions", [])

        for d in dims:
            if d.get("percentage", 0) >= 80:
                strengths.append({
                    "dimension": d["name"],
                    "score": d["score"],
                    "max_score": d["max_score"],
                    "description": d.get("feedback", ""),
                    "evidence": self._get_evidence(d["name"], vision, vibe, stt),
                })

        # 특수 강점 감지
        if vision.get("eye_contact_ratio", 0) > 0.7:
            strengths.append({"dimension": "시선 접촉", "description": "학생들과의 시선 접촉이 매우 우수합니다.", "evidence": f"시선 접촉률: {vision['eye_contact_ratio']:.0%}"})
        if vision.get("gesture_active_ratio", 0) > 0.5:
            strengths.append({"dimension": "제스처 활용", "description": "적극적인 제스처로 내용 전달력을 높이고 있습니다.", "evidence": f"제스처 활성률: {vision['gesture_active_ratio']:.0%}"})
        if stt.get("filler_ratio", 1) < 0.02:
            strengths.append({"dimension": "언어 정제", "description": "습관어 사용이 매우 적어 전달력이 높습니다.", "evidence": f"습관어 비율: {stt.get('filler_ratio', 0):.1%}"})

        return strengths[:5]

    def _identify_improvements(self, ped: Dict, vision: Dict, vibe: Dict, stt: Dict) -> List[Dict]:
        """개선점 식별"""
        improvements = []
        dims = ped.get("dimensions", [])

        for d in sorted(dims, key=lambda x: x.get("percentage", 100)):
            if d.get("percentage", 100) < 75:
                improvements.append({
                    "dimension": d["name"],
                    "score": d["score"],
                    "max_score": d["max_score"],
                    "current_level": d.get("grade", ""),
                    "feedback": d.get("feedback", ""),
                    "tips": d.get("improvement_tips", []),
                    "priority": "높음" if d.get("percentage", 0) < 60 else "보통",
                })

        # 특수 개선점 감지
        if vision.get("eye_contact_ratio", 0) < 0.3:
            improvements.append({"dimension": "시선 접촉", "feedback": "학생들과의 시선 접촉을 늘리세요.", "priority": "높음",
                                 "tips": ["교실 전체를 골고루 바라보세요.", "특정 학생에게만 시선이 집중되지 않도록 하세요."]})
        if vibe.get("monotone_ratio", 0) > 0.5:
            improvements.append({"dimension": "음성 변화", "feedback": "목소리의 톤 변화를 주세요.", "priority": "보통",
                                 "tips": ["강조할 내용에서는 목소리를 높이세요.", "중요한 부분에서 잠시 멈춤(pause)을 활용하세요."]})

        return improvements[:5]

    def _create_action_plan(self, improvements: List[Dict]) -> List[Dict]:
        """단계별 실행 계획 생성"""
        plan = []
        for i, imp in enumerate(improvements[:3], 1):
            tips = imp.get("tips", [])
            plan.append({
                "step": i,
                "target": imp.get("dimension", ""),
                "priority": imp.get("priority", "보통"),
                "goal": imp.get("feedback", ""),
                "actions": tips[:3] if tips else [f"{imp.get('dimension', '')} 역량을 점진적으로 강화하세요."],
                "timeline": "1주" if imp.get("priority") == "높음" else "2주",
            })
        return plan

    def _get_evidence(self, dim_name: str, vision: Dict, vibe: Dict, stt: Dict) -> str:
        """차원별 근거 데이터 추출"""
        evidence_map = {
            "수업 전문성": f"단어 수: {stt.get('word_count', 'N/A')}, 발화 속도: {stt.get('speaking_rate', 'N/A')} WPM",
            "교수학습 방법": f"제스처 활성률: {vision.get('gesture_active_ratio', 0):.0%}",
            "판서 및 언어": f"습관어 비율: {stt.get('filler_ratio', 0):.1%}",
            "수업 태도": f"시선 접촉률: {vision.get('eye_contact_ratio', 0):.0%}",
            "학생 참여": f"발화 패턴: {stt.get('speaking_pattern', 'N/A')}",
            "시간 배분": f"단조로움 비율: {vibe.get('monotone_ratio', 0):.0%}",
            "창의성": f"움직임 점수: {vision.get('avg_motion_score', 0):.1f}",
        }
        return evidence_map.get(dim_name, "")

    def _generate_llm_summary(self, ped: Dict, strengths: List, improvements: List) -> str:
        """Gemini LLM 기반 종합 요약"""
        try:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                return self._generate_rule_summary(ped, strengths, improvements)

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"""다음 수업 분석 결과를 바탕으로 200자 이내의 종합 피드백을 한국어로 작성하세요.
총점: {ped.get('total_score', 0)}점 / 100점 ({ped.get('grade', '')})
강점: {', '.join(s.get('dimension', '') for s in strengths)}
개선점: {', '.join(i.get('dimension', '') for i in improvements)}
격려와 구체적 조언을 포함하세요."""

            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return self._generate_rule_summary(ped, strengths, improvements)

    def _generate_rule_summary(self, ped: Dict, strengths: List, improvements: List) -> str:
        """규칙 기반 종합 요약"""
        score = ped.get("total_score", 0)
        grade = ped.get("grade", "")
        s_names = ", ".join(s.get("dimension", "") for s in strengths[:3]) or "전반적으로 고르게 발전하고 있습니다"
        i_names = ", ".join(i.get("dimension", "") for i in improvements[:2]) or "없음"

        if score >= 85:
            opening = f"전체 {score}점({grade})으로 매우 우수한 수업입니다! 🎉"
        elif score >= 70:
            opening = f"전체 {score}점({grade})으로 양호한 수업입니다. 👍"
        else:
            opening = f"전체 {score}점({grade})입니다. 지속적인 발전이 기대됩니다. 💪"

        return f"{opening} 강점은 [{s_names}]이며, [{i_names}] 영역의 보완을 통해 더 나은 수업이 될 수 있습니다."
