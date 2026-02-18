"""
📚 Pedagogy Agent - 교육학 이론 기반 평가 전문 에이전트
v5.0: YAML 루브릭 설정 + 화자분리/발화분석 통합 + 점수 범위 ±5.0

v5.0 개선:
- 외부 rubric_config.yaml 로드 (수업 유형별 프리셋)
- 화자 분리 데이터 (student_turns, interaction_count) → 학생 참여 직접 측정
- DiscourseAnalyzer 결과 (질문 유형, 피드백 품질, Bloom 수준) 통합
- 점수 조정 범위 확대: ±3.0 → ±5.0 (더 넓은 변별력)
"""

from typing import Dict, List
from dataclasses import dataclass, field
from pathlib import Path

# YAML 로드
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# 기본 프레임워크 (YAML 로드 실패 시 폴백)
DEFAULT_DIMENSIONS = {
    "수업 전문성": {"weight": 20, "theory": "구성주의 학습이론 - 학습 목표의 명확한 제시는 학생의 인지적 스캐폴딩을 제공합니다."},
    "교수학습 방법": {"weight": 20, "theory": "다중지능이론(Gardner) - 다양한 교수법은 학생의 다양한 학습 양식에 대응합니다."},
    "판서 및 언어": {"weight": 15, "theory": "Vygotsky의 근접발달영역(ZPD) - 명확한 언어 사용은 효과적인 비계설정의 핵심입니다."},
    "수업 태도": {"weight": 15, "theory": "Bandura의 사회학습이론 - 교사의 열정과 태도는 학생의 학습 동기에 직접적으로 영향을 미칩니다."},
    "학생 참여": {"weight": 15, "theory": "구성주의적 참여이론(Engagement Theory) - 학생의 능동적 참여는 심층 학습의 핵심 요소입니다."},
    "시간 배분": {"weight": 10, "theory": "Keller의 ARCS 모델 - 체계적 시간 배분은 학습자의 주의와 만족에 기여합니다."},
    "창의성": {"weight": 5, "theory": "창의적 문제해결(Torrance) - 독창적 수업 설계는 학생의 확산적 사고를 자극합니다."},
}

DEFAULT_PRESETS = {
    "default": {
        "수업 전문성": {"base": 14.0, "adjust_range": 5.0},
        "교수학습 방법": {"base": 14.0, "adjust_range": 5.0},
        "판서 및 언어": {"base": 10.0, "adjust_range": 4.0},
        "수업 태도": {"base": 10.0, "adjust_range": 4.0},
        "학생 참여": {"base": 10.0, "adjust_range": 4.0},
        "시간 배분": {"base": 7.0, "adjust_range": 2.5},
        "창의성": {"base": 3.0, "adjust_range": 1.5},
    }
}

DEFAULT_GRADING = {
    "A+": 90, "A": 85, "A-": 80, "B+": 75, "B": 70,
    "B-": 65, "C+": 60, "C": 55, "C-": 50, "D": 0,
}


@dataclass
class DimensionScore:
    name: str
    score: float
    max_score: float
    percentage: float
    grade: str
    feedback: str
    theory_reference: str
    improvement_tips: List[str] = field(default_factory=list)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}


def _safe(d: Dict, key: str, default=None):
    """에이전트 데이터에서 안전하게 값 추출 (error 딕셔너리 처리)"""
    if not d or not isinstance(d, dict) or 'error' in d:
        return default
    return d.get(key, default)


class PedagogyAgent:
    """📚 교육학 이론 기반 7차원 평가 에이전트 (v5.0 — 종합 개선)"""

    def __init__(self, use_rag: bool = True, preset: str = "default"):
        self.use_rag = use_rag
        self.preset = preset
        self._rag_kb = None

        # YAML 설정 로드
        self.dimensions, self.presets, self.grading = self._load_config()
        self.current_preset = self.presets.get(preset, self.presets.get("default", {}))

    def _load_config(self):
        """rubric_config.yaml 로드 (실패 시 기본값)"""
        config_path = Path(__file__).resolve().parent.parent.parent / "config" / "rubric_config.yaml"

        if HAS_YAML and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = yaml.safe_load(f)

                dims = {}
                for name, d in cfg.get("dimensions", {}).items():
                    # YAML의 underscore 이름을 space로 변환
                    display_name = name.replace("_", " ")
                    dims[display_name] = {"weight": d["weight"], "theory": d["theory"]}

                presets = {}
                for pname, pvals in cfg.get("presets", {}).items():
                    preset_data = {}
                    for dname, dvals in pvals.items():
                        display_name = dname.replace("_", " ")
                        preset_data[display_name] = dvals
                    presets[pname] = preset_data

                grading = cfg.get("grading", DEFAULT_GRADING)
                return dims, presets, grading
            except Exception as e:
                print(f"[PedagogyAgent] YAML 설정 로드 실패: {e}")

        return DEFAULT_DIMENSIONS, DEFAULT_PRESETS, DEFAULT_GRADING

    def evaluate(self, vision_summary: Dict, content_summary: Dict,
                 vibe_summary: Dict, stt_result: Dict = None,
                 discourse_result: Dict = None) -> Dict:
        """
        7차원 종합 평가

        Args:
            vision_summary: VisionAgent 분석 결과
            content_summary: ContentAgent 분석 결과
            vibe_summary: VibeAgent 분석 결과
            stt_result: STTAgent 분석 결과
            discourse_result: DiscourseAnalyzer 분석 결과 (v5.0)
        """
        stt = stt_result or {}
        discourse = discourse_result or {}

        # 에이전트 데이터 유효성 확인
        vis_ok = bool(vision_summary and 'error' not in vision_summary)
        con_ok = bool(content_summary and 'error' not in content_summary)
        vib_ok = bool(vibe_summary and len(vibe_summary) > 0)
        stt_ok = bool(stt and 'word_count' in stt)
        disc_ok = bool(discourse and 'question_types' in discourse)

        dimensions = [
            self._eval_expertise(content_summary, stt, vis_ok, con_ok, stt_ok, discourse, disc_ok),
            self._eval_methods(content_summary, vision_summary, stt, vis_ok, con_ok, stt_ok, discourse, disc_ok),
            self._eval_language(content_summary, stt, vibe_summary, stt_ok, vib_ok),
            self._eval_attitude(vision_summary, vibe_summary, vis_ok, vib_ok, stt_ok, stt, discourse, disc_ok),
            self._eval_participation(stt, vibe_summary, stt_ok, vib_ok, discourse, disc_ok),
            self._eval_time(vibe_summary, stt, vib_ok, stt_ok),
            self._eval_creativity(content_summary, vision_summary, stt, vibe_summary, vis_ok, con_ok, stt_ok, vib_ok, discourse, disc_ok),
        ]
        total = sum(d.score for d in dimensions)
        return {
            "total_score": round(total, 1),
            "grade": self._grade(total),
            "dimensions": [d.to_dict() for d in dimensions],
            "dimension_scores": {d.name: d.score for d in dimensions},
            "theory_references": [d.theory_reference for d in dimensions],
            "preset_used": self.preset,
        }

    def _get_base(self, dim_name: str) -> float:
        """프리셋에서 기본점 가져오기"""
        p = self.current_preset.get(dim_name, {})
        return p.get("base", 10.0)

    def _make_score(self, name, base, feedback_fn, tips=None):
        w = self.dimensions.get(name, DEFAULT_DIMENSIONS.get(name, {})).get("weight", 10)
        score = max(0, min(w, round(base, 1)))
        pct = (score / w) * 100
        g = "우수" if pct >= 85 else ("양호" if pct >= 70 else ("보통" if pct >= 55 else "노력 필요"))
        theory = self.dimensions.get(name, DEFAULT_DIMENSIONS.get(name, {})).get("theory", "")
        return DimensionScore(name=name, score=score, max_score=w, percentage=pct, grade=g,
                              feedback=feedback_fn(pct),
                              theory_reference=theory,
                              improvement_tips=tips or [])

    # ================================================================
    # 1. 수업 전문성 (20점) — v5.0: Bloom 인지수준 반영
    # ================================================================
    def _eval_expertise(self, content, stt, vis_ok, con_ok, stt_ok, discourse, disc_ok):
        base = self._get_base("수업 전문성")

        if stt_ok:
            wc = stt.get('word_count', 0)
            dur = stt.get('duration_seconds', 600)
            wpm = (wc / dur * 60) if dur > 0 else 0

            if wc > 1200:
                base += 3.5
            elif wc > 800:
                base += 2.0
            elif wc > 500:
                base += 0.5
            elif wc > 300:
                base -= 2.0
            else:
                base -= 4.0

            if 70 <= wpm <= 100:
                base += 1.5
            elif 55 <= wpm <= 120:
                base += 0.5
            elif wpm > 140:
                base -= 2.0
            elif wpm < 40:
                base -= 2.0

        if con_ok:
            slide_r = _safe(content, 'slide_detected_ratio', 0)
            if slide_r > 0.5:
                base += 2.0
            elif slide_r > 0.3:
                base += 1.0
            elif slide_r < 0.1:
                base -= 1.0

        # v5.0: Bloom 인지수준 반영
        if disc_ok:
            bloom = discourse.get('bloom_levels', {})
            higher_order = bloom.get('analyze', 0) + bloom.get('evaluate', 0) + bloom.get('create', 0)
            if higher_order > 0.3:
                base += 2.0  # 고차원 사고 비중 높음
            elif higher_order > 0.15:
                base += 1.0
            elif higher_order < 0.05:
                base -= 1.0  # 암기 중심 수업

        tips = []
        if stt_ok and stt.get('word_count', 0) < 500:
            tips.append("충분한 설명을 통해 학습 내용을 풍부하게 전달하세요.")
        if disc_ok and discourse.get('bloom_levels', {}).get('analyze', 0) < 0.1:
            tips.append("분석·평가·창작 수준의 사고를 유도하는 질문을 늘리세요.")

        return self._make_score("수업 전문성", base,
            lambda p: "학습 목표가 명확하고 내용 구조화가 매우 체계적입니다." if p >= 85 else
                      ("학습 목표와 내용 구성이 전반적으로 양호합니다." if p >= 70 else
                       ("내용 전달이 보통 수준입니다. 구조화가 필요합니다." if p >= 55 else
                        "학습 목표를 명확히 하고 내용을 체계적으로 구성하세요.")), tips)

    # ================================================================
    # 2. 교수학습 방법 (20점) — v5.0: 질문 유형/스캐폴딩 반영
    # ================================================================
    def _eval_methods(self, content, vision, stt, vis_ok, con_ok, stt_ok, discourse, disc_ok):
        base = self._get_base("교수학습 방법")

        if con_ok:
            slide_r = _safe(content, 'slide_detected_ratio', 0)
            if slide_r > 0.6:
                base += 2.5
            elif slide_r > 0.3:
                base += 1.0
            elif slide_r < 0.1:
                base -= 1.5

            contrast = _safe(content, 'avg_color_contrast', 0)
            if contrast > 60:
                base += 1.0
            elif contrast < 20:
                base -= 0.5

        if vis_ok:
            g = _safe(vision, 'gesture_active_ratio', 0)
            if g > 0.5:
                base += 2.5
            elif g > 0.3:
                base += 1.0
            elif g < 0.1:
                base -= 1.5

            motion = _safe(vision, 'avg_motion_score', 0)
            if motion > 25:
                base += 1.0
            elif motion < 5:
                base -= 0.5

        if stt_ok:
            wc = stt.get('word_count', 0)
            dur = stt.get('duration_seconds', 600)
            wpm = (wc / dur * 60) if dur > 0 else 0
            if wpm > 90:
                base += 2.0
            elif wpm > 70:
                base += 1.0
            elif wpm < 45:
                base -= 2.0

        # v5.0: 질문 유형 분석
        if disc_ok:
            qt = discourse.get('question_types', {})
            total_q = sum(qt.values()) or 1
            open_ratio = qt.get('open_ended', 0) / total_q
            scaffolding = qt.get('scaffolding', 0)

            if open_ratio > 0.4:
                base += 2.0  # 개방형 질문 40% 이상
            elif open_ratio > 0.2:
                base += 1.0
            elif open_ratio < 0.05:
                base -= 1.0  # 거의 폐쇄형만

            if scaffolding >= 3:
                base += 1.5  # 스캐폴딩 질문 다수
            elif scaffolding >= 1:
                base += 0.5

        tips = []
        if disc_ok:
            qt = discourse.get('question_types', {})
            if qt.get('open_ended', 0) < 3:
                tips.append("'왜?', '어떻게?' 등 개방형 질문을 더 활용하세요.")
            if qt.get('scaffolding', 0) < 1:
                tips.append("스캐폴딩 질문으로 학생의 사고를 단계적으로 유도하세요.")

        return self._make_score("교수학습 방법", base,
            lambda p: "다양한 교수학습 방법을 매우 효과적으로 활용합니다." if p >= 85 else
                      ("교수법이 양호하며 시각자료 활용도 적절합니다." if p >= 70 else
                       ("교수법이 보통 수준입니다. 다양한 전략을 시도하세요." if p >= 55 else
                        "다양한 교수학습 전략과 매체 활용이 필요합니다.")), tips)

    # ================================================================
    # 3. 판서 및 언어 (15점)
    # ================================================================
    def _eval_language(self, content, stt, vibe, stt_ok, vib_ok):
        base = self._get_base("판서 및 언어")

        if stt_ok:
            fr = stt.get('filler_ratio', 0.03)
            if fr < 0.015:
                base += 3.0
            elif fr < 0.025:
                base += 1.5
            elif fr < 0.035:
                base += 0.5
            elif fr > 0.07:
                base -= 3.0
            elif fr > 0.05:
                base -= 2.0
            elif fr > 0.04:
                base -= 1.0

            pat = stt.get('speaking_pattern', '')
            if '빠름' in pat or 'Fast' in pat:
                base -= 1.0
            elif '느림' in pat or 'Slow' in pat:
                base -= 0.5

        if vib_ok:
            mono = _safe(vibe, 'monotone_ratio', 0.5)
            if mono < 0.2:
                base += 2.0
            elif mono < 0.3:
                base += 1.0
            elif mono > 0.6:
                base -= 2.0
            elif mono > 0.4:
                base -= 1.0

        tips = []
        if stt_ok and stt.get('filler_ratio', 0) > 0.04:
            tips.append(f"습관어를 줄이세요 (현재: {stt.get('filler_ratio', 0):.1%}).")
        if not vib_ok:
            tips.append("목소리 톤에 변화를 주어 핵심 내용을 강조하세요.")

        return self._make_score("판서 및 언어", base,
            lambda p: "언어 표현이 명확하고 발화가 매우 깨끗합니다." if p >= 85 else
                      ("언어 사용이 양호하나 미세한 개선 여지가 있습니다." if p >= 70 else
                       ("습관어나 단조로운 어조 개선이 필요합니다." if p >= 55 else
                        "발화 습관을 개선하고 핵심 용어를 정확히 사용하세요.")), tips)

    # ================================================================
    # 4. 수업 태도 (15점) — v5.0: 구체적 칭찬/교정 피드백 반영
    # ================================================================
    def _eval_attitude(self, vision, vibe, vis_ok, vib_ok, stt_ok, stt, discourse, disc_ok):
        base = self._get_base("수업 태도")

        if vis_ok:
            ec = _safe(vision, 'eye_contact_ratio', 0)
            if ec > 0.7:
                base += 3.0
            elif ec > 0.5:
                base += 2.0
            elif ec > 0.3:
                base += 0.5
            elif ec < 0.15:
                base -= 2.0

            expr = _safe(vision, 'avg_expression_score', 50)
            if expr > 70:
                base += 2.0
            elif expr > 55:
                base += 0.5
            elif expr < 30:
                base -= 1.5

        if vib_ok:
            ed = _safe(vibe, 'energy_distribution', {})
            if ed:
                high_e = ed.get('high', 0)
                low_e = ed.get('low', 0)
                if high_e > 0.4:
                    base += 2.0
                elif high_e > 0.25:
                    base += 0.5
                if low_e > 0.5:
                    base -= 1.5

        if stt_ok:
            wc = stt.get('word_count', 0)
            dur = stt.get('duration_seconds', 600)
            wpm = (wc / dur * 60) if dur > 0 else 0
            if wpm > 90:
                base += 1.5
            elif wpm < 40:
                base -= 1.5

        # v5.0: 피드백 품질 반영
        if disc_ok:
            fb = discourse.get('feedback_quality', {})
            specific_praise = fb.get('specific_praise', 0)
            corrective = fb.get('corrective', 0)
            if specific_praise >= 5:
                base += 2.0  # 구체적 칭찬이 많음
            elif specific_praise >= 2:
                base += 1.0
            if corrective >= 3:
                base += 1.0  # 교정 피드백도 좋은 태도

        tips = []
        if vis_ok and _safe(vision, 'eye_contact_ratio', 0) < 0.3:
            tips.append("학생들과 시선을 고르게 맞추며 소통하세요.")
        if disc_ok and discourse.get('feedback_quality', {}).get('specific_praise', 0) < 2:
            tips.append("'잘했어요' 대신 '○○을 정확히 파악했네!'와 같은 구체적 칭찬을 하세요.")

        return self._make_score("수업 태도", base,
            lambda p: "열정적인 태도와 학생과의 라포 형성이 매우 우수합니다." if p >= 85 else
                      ("전반적으로 양호한 태도이나 소통 강화가 필요합니다." if p >= 70 else
                       ("태도 전반에 개선이 필요합니다." if p >= 55 else
                        "시선 접촉과 구체적 피드백을 통해 열정을 전달하세요.")), tips)

    # ================================================================
    # 5. 학생 참여 (15점) — v5.0: 화자분리 직접 활용
    # ================================================================
    def _eval_participation(self, stt, vibe, stt_ok, vib_ok, discourse, disc_ok):
        base = self._get_base("학생 참여")

        if stt_ok:
            # v5.0: 화자 분리 데이터 직접 활용
            student_turns = stt.get('student_turns', 0)
            interaction_count = stt.get('interaction_count', 0)
            teacher_ratio = stt.get('teacher_ratio', 0.75)

            if student_turns > 15:
                base += 3.5  # 학생 발화 매우 활발
            elif student_turns > 8:
                base += 2.0
            elif student_turns > 3:
                base += 0.5
            elif student_turns == 0:
                base -= 2.0  # 학생 발화 없음

            if interaction_count > 20:
                base += 2.0  # 활발한 교대
            elif interaction_count > 10:
                base += 1.0

            if teacher_ratio < 0.6:
                base += 1.5  # 학생 주도적
            elif teacher_ratio > 0.9:
                base -= 1.5  # 교사 일방적

            # 질문 횟수
            question_count = stt.get('question_count', 0)
            if question_count > 10:
                base += 1.5
            elif question_count > 5:
                base += 0.5

            # 발화 패턴
            pat = stt.get('speaking_pattern', '')
            if 'Conversational' in pat or '대화' in pat:
                base += 1.0

        if vib_ok:
            sr = _safe(vibe, 'avg_silence_ratio', 0.3)
            if 0.15 <= sr <= 0.30:
                base += 1.0
            elif sr < 0.05:
                base -= 0.5
            elif sr > 0.45:
                base -= 1.0

        # v5.0: 상호작용 점수 반영
        if disc_ok:
            interaction_score = discourse.get('interaction_score', 50)
            if interaction_score > 75:
                base += 2.0
            elif interaction_score > 60:
                base += 1.0
            elif interaction_score < 35:
                base -= 1.0

        tips = []
        if stt_ok and stt.get('student_turns', 0) < 3:
            tips.append("개방형 질문으로 학생 발언 기회를 늘리세요.")
        if stt_ok and stt.get('teacher_ratio', 0.75) > 0.85:
            tips.append("교사 발화 비율이 높습니다. 학생에게 더 많은 발언 기회를 주세요.")

        return self._make_score("학생 참여", base,
            lambda p: "학생 참여를 효과적으로 이끌어내며 상호작용이 활발합니다." if p >= 85 else
                      ("참여 유도가 양호하나 상호작용을 더 늘리세요." if p >= 70 else
                       ("학생 참여 유도가 부족합니다." if p >= 55 else
                        "발문과 피드백 전략을 적극적으로 활용하세요.")), tips)

    # ================================================================
    # 6. 시간 배분 (10점)
    # ================================================================
    def _eval_time(self, vibe, stt, vib_ok, stt_ok):
        base = self._get_base("시간 배분")

        if vib_ok:
            ed = _safe(vibe, 'energy_distribution', {})
            if ed:
                lvs = [ed.get('low', 0), ed.get('normal', 0), ed.get('high', 0)]
                if sum(lvs) > 0:
                    spread = max(lvs) - min(lvs)
                    if spread < 0.25:
                        base += 2.5
                    elif spread < 0.4:
                        base += 1.0
                    elif spread > 0.65:
                        base -= 1.5

            mono = _safe(vibe, 'monotone_ratio', 0.5)
            if mono < 0.2:
                base += 1.0
            elif mono > 0.5:
                base -= 1.0

        if stt_ok:
            dur = stt.get('duration_seconds', 600)
            if 500 <= dur <= 900:
                base += 0.5
            elif dur > 1200:
                base -= 1.0
            elif dur < 300:
                base -= 1.0

        tips = []
        if base < 7:
            tips.append("도입(10%)-전개(70%)-정리(20%) 비율로 시간을 배분하세요.")

        return self._make_score("시간 배분", base,
            lambda p: "시간 배분이 매우 적절하며 수업 흐름이 자연스럽습니다." if p >= 85 else
                      ("시간 배분이 양호하나 정리 단계를 확보하세요." if p >= 70 else
                       ("시간 배분에 개선이 필요합니다." if p >= 55 else
                        "시간 배분을 사전에 계획하고 각 단계에 충실하세요.")), tips)

    # ================================================================
    # 7. 창의성 (5점) — v5.0: 발화 다양성 + 시각자료 복합 평가
    # ================================================================
    def _eval_creativity(self, content, vision, stt, vibe, vis_ok, con_ok, stt_ok, vib_ok, discourse, disc_ok):
        base = self._get_base("창의성")

        if con_ok:
            slide_r = _safe(content, 'slide_detected_ratio', 0)
            if slide_r > 0.5:
                base += 1.0
            elif slide_r > 0.3:
                base += 0.5

            contrast = _safe(content, 'avg_color_contrast', 0)
            if contrast > 60:
                base += 0.5
            elif contrast < 20:
                base -= 0.3

        if vis_ok:
            motion = _safe(vision, 'avg_motion_score', 0)
            if motion > 25:
                base += 0.5
            openness = _safe(vision, 'avg_body_openness', 0.5)
            if openness > 0.7:
                base += 0.5

        if stt_ok:
            wc = stt.get('word_count', 0)
            sc = stt.get('segment_count', 1)
            dur = stt.get('duration_seconds', 600)
            wpm = (wc / dur * 60) if dur > 0 else 0

            if sc > 100 and wc > 800:
                base += 1.0
            elif sc > 60 and wc > 500:
                base += 0.5
            elif wc < 300:
                base -= 0.5

        # v5.0: 고차원 인지 + 스캐폴딩 → 창의적 수업
        if disc_ok:
            bloom = discourse.get('bloom_levels', {})
            create_level = bloom.get('create', 0)
            if create_level > 0.1:
                base += 0.8
            scaffolding = discourse.get('question_types', {}).get('scaffolding', 0)
            if scaffolding >= 2:
                base += 0.5

        tips = []
        if base < 3.5:
            tips.append("ICT 도구를 활용한 창의적 수업 설계를 시도하세요.")

        return self._make_score("창의성", base,
            lambda p: "창의적인 수업 설계와 전달이 돋보입니다." if p >= 85 else
                      ("창의성이 양호한 수준입니다." if p >= 70 else
                       ("창의적 요소를 더 추가하세요." if p >= 55 else
                        "독창적인 활동과 시각적 매체를 적극 활용하세요.")), tips)

    def _grade(self, total):
        for g, threshold in sorted(self.grading.items(), key=lambda x: x[1], reverse=True):
            if total >= threshold:
                return g
        return "D"
