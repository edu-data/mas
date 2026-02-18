"""
💡 Feedback Agent - 맞춤형 피드백 생성 전문 에이전트
v5.0: 발화 분석(DiscourseAnalyzer) 결과 반영 + 타임스탬프 기반 피드백
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
    💡 Feedback Agent v5.0
    모든 분석 에이전트의 결과를 종합하여 구체적이고 실행 가능한
    수업 개선 피드백을 생성합니다.

    v5.0 추가:
    - 화자 분리 + 발화 분석 결과 통합
    - Bloom 인지수준 기반 교수법 제안
    - 상호작용 패턴 기반 학생 참여 피드백
    """

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm and HAS_GENAI and os.getenv("GOOGLE_API_KEY")

    def generate(
        self,
        pedagogy_result: Dict,
        vision_summary: Dict = None,
        content_summary: Dict = None,
        vibe_summary: Dict = None,
        stt_result: Dict = None,
        discourse_result: Dict = None,
    ) -> Dict:
        """
        종합 피드백 생성

        Args:
            pedagogy_result: PedagogyAgent 평가 결과
            vision_summary: VisionAgent 요약
            content_summary: ContentAgent 요약
            vibe_summary: VibeAgent 요약
            stt_result: STTAgent 결과
            discourse_result: DiscourseAnalyzer 결과 (v5.0)

        Returns:
            strengths, improvements, action_plan, overall_summary
        """
        ped = pedagogy_result or {}
        vision = vision_summary or {}
        vibe = vibe_summary or {}
        stt = stt_result or {}
        discourse = discourse_result or {}

        strengths = self._identify_strengths(ped, vision, vibe, stt, discourse)
        improvements = self._identify_improvements(ped, vision, vibe, stt, discourse)
        action_plan = self._create_action_plan(improvements)

        if self.use_llm:
            summary = self._generate_llm_summary(ped, strengths, improvements, discourse)
        else:
            summary = self._generate_rule_summary(ped, strengths, improvements, discourse)

        return {
            "strengths": strengths,
            "improvements": improvements,
            "action_plan": action_plan,
            "overall_summary": summary,
        }

    def _identify_strengths(self, ped: Dict, vision: Dict, vibe: Dict,
                            stt: Dict, discourse: Dict) -> List[Dict]:
        """강점 식별"""
        strengths = []
        dims = ped.get("dimensions", [])

        for dim in dims:
            if dim.get("percentage", 0) >= 75:
                strengths.append({
                    "dimension": dim["name"],
                    "score": dim["score"],
                    "percentage": dim["percentage"],
                    "feedback": dim.get("feedback", ""),
                })

        # v5.0: 발화 분석 기반 강점
        if discourse:
            qt = discourse.get("question_types", {})
            if qt.get("open_ended", 0) >= 3:
                strengths.append({
                    "dimension": "개방형 질문 활용",
                    "detail": f"개방형 질문 {qt['open_ended']}회 사용 — 학생 사고를 자극합니다.",
                    "source": "discourse_analysis",
                })

            fb = discourse.get("feedback_quality", {})
            if fb.get("specific_praise", 0) >= 3:
                strengths.append({
                    "dimension": "구체적 칭찬",
                    "detail": f"구체적 칭찬 {fb['specific_praise']}회 — 학생 동기 부여에 효과적입니다.",
                    "source": "discourse_analysis",
                })

        # 화자 분리 기반 강점
        if stt.get("student_turns", 0) > 8:
            strengths.append({
                "dimension": "학생 참여 유도",
                "detail": f"학생 발화 {stt['student_turns']}회 — 활발한 상호작용이 이루어지고 있습니다.",
                "source": "speaker_diarization",
            })

        return strengths

    def _identify_improvements(self, ped: Dict, vision: Dict, vibe: Dict,
                               stt: Dict, discourse: Dict) -> List[Dict]:
        """개선점 식별"""
        improvements = []
        dims = ped.get("dimensions", [])

        for dim in dims:
            if dim.get("percentage", 0) < 65:
                improvements.append({
                    "dimension": dim["name"],
                    "score": dim["score"],
                    "percentage": dim["percentage"],
                    "tips": dim.get("improvement_tips", []),
                    "priority": "high" if dim["percentage"] < 55 else "medium",
                })

        # v5.0: 발화 분석 기반 개선점
        if discourse:
            qt = discourse.get("question_types", {})
            total_q = sum(qt.values()) or 1
            if qt.get("open_ended", 0) / total_q < 0.1:
                improvements.append({
                    "dimension": "질문 전략",
                    "detail": "개방형 질문이 부족합니다. '왜?', '어떻게?' 질문을 활용하세요.",
                    "priority": "high",
                    "source": "discourse_analysis",
                })

            bloom = discourse.get("bloom_levels", {})
            higher_order = bloom.get("analyze", 0) + bloom.get("evaluate", 0) + bloom.get("create", 0)
            if higher_order < 0.1:
                improvements.append({
                    "dimension": "인지수준",
                    "detail": "암기·이해 수준의 수업이 주를 이루고 있습니다. 분석·평가 활동을 추가하세요.",
                    "priority": "medium",
                    "source": "discourse_analysis",
                })

        # 화자 분리 기반 개선점
        if stt.get("teacher_ratio", 0.75) > 0.9:
            improvements.append({
                "dimension": "교사-학생 발화 균형",
                "detail": f"교사 발화 비율 {stt['teacher_ratio']:.0%}로 일방적입니다. 학생 발언 기회를 늘리세요.",
                "priority": "high",
                "source": "speaker_diarization",
            })

        return improvements

    def _create_action_plan(self, improvements: List[Dict]) -> List[Dict]:
        """단계별 실행 계획 생성"""
        plan = []
        prioritized = sorted(improvements, key=lambda x: 0 if x.get("priority") == "high" else 1)

        for i, imp in enumerate(prioritized[:5], 1):
            dim = imp.get("dimension", "")
            tips = imp.get("tips", [])
            detail = imp.get("detail", "")

            plan.append({
                "step": i,
                "area": dim,
                "action": tips[0] if tips else detail or f"{dim} 영역 개선 필요",
                "priority": imp.get("priority", "medium"),
            })

        return plan

    def _get_evidence(self, dim_name: str, vision: Dict, vibe: Dict, stt: Dict) -> str:
        """차원별 근거 데이터 추출"""
        evidence = []
        if "시선" in dim_name or "태도" in dim_name:
            if vision:
                evidence.append(f"시선 접촉 {vision.get('eye_contact_ratio', 0):.0%}")
        if "언어" in dim_name:
            if stt:
                evidence.append(f"습관어 비율 {stt.get('filler_ratio', 0):.1%}")
        if "참여" in dim_name:
            if stt:
                evidence.append(f"학생 발화 {stt.get('student_turns', 0)}회")
                evidence.append(f"상호작용 교대 {stt.get('interaction_count', 0)}회")
        return ", ".join(evidence) if evidence else "데이터 부족"

    def _generate_llm_summary(self, ped: Dict, strengths: List,
                              improvements: List, discourse: Dict) -> str:
        """Gemini LLM 기반 종합 요약"""
        try:
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("gemini-2.0-flash")

            score = ped.get("total_score", 0)
            grade = ped.get("grade", "")
            disc_info = ""
            if discourse:
                disc_info = f"""
발화 분석:
- 질문 유형: {discourse.get('question_types', {})}
- 피드백 품질: {discourse.get('feedback_quality', {})}
- Bloom 인지수준: {discourse.get('bloom_levels', {})}
- 상호작용 점수: {discourse.get('interaction_score', 'N/A')}"""

            prompt = f"""수업 분석 결과를 바탕으로 한국어로 200자 종합 요약을 생성하세요.
총점: {score}/100 ({grade})
강점: {[s['dimension'] for s in strengths]}
개선점: {[i['dimension'] for i in improvements]}{disc_info}"""

            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return self._generate_rule_summary(ped, strengths, improvements, discourse)

    def _generate_rule_summary(self, ped: Dict, strengths: List,
                               improvements: List, discourse: Dict) -> str:
        """규칙 기반 종합 요약"""
        score = ped.get("total_score", 0)
        grade = ped.get("grade", "N/A")

        summary = f"총점 {score:.1f}/100 ({grade}등급). "

        if strengths:
            s_names = [s["dimension"] for s in strengths[:3]]
            summary += f"강점: {', '.join(s_names)}. "

        if improvements:
            i_names = [i["dimension"] for i in improvements[:3]]
            summary += f"개선 필요: {', '.join(i_names)}. "

        if discourse and discourse.get("interaction_score", 50) > 70:
            summary += "학생과의 상호작용이 활발하여 호응을 이끌어내고 있습니다. "

        return summary.strip()
