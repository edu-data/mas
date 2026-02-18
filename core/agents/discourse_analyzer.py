"""
📝 Discourse Analyzer - 발화 내용 교육학적 분석
v5.0: Gemini LLM 기반 질문 유형 분류, 피드백 품질 분석, Bloom 인지수준 측정
"""

import os
import re
from typing import Dict, List, Optional

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class DiscourseAnalyzer:
    """
    📝 발화 내용 교육학적 분석

    LLM 기반 분석:
    - 질문 유형 분류 (개방형/폐쇄형/수사적/스캐폴딩)
    - 피드백 품질 (구체적 칭찬/교정적/일반적)
    - Bloom 인지수준 분포
    - 상호작용 품질 점수

    폴백: 규칙 기반 패턴 매칭
    """

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm and HAS_GENAI and os.getenv("GOOGLE_API_KEY")
        if self.use_llm:
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

    def analyze(self, transcript: str, segments: List[Dict] = None,
                speaker_segments: List[Dict] = None) -> Dict:
        """
        발화 텍스트 교육학적 분석

        Args:
            transcript: 전체 발화 텍스트
            segments: STT 세그먼트 목록
            speaker_segments: 화자 분리 결과

        Returns:
            분석 결과 딕셔너리
        """
        if not transcript or len(transcript) < 20:
            return self._empty_result()

        if self.use_llm:
            try:
                return self._analyze_llm(transcript, speaker_segments)
            except Exception as e:
                print(f"[DiscourseAnalyzer] LLM 분석 실패, 규칙 기반 전환: {e}")

        return self._analyze_rules(transcript, segments, speaker_segments)

    def _analyze_llm(self, transcript: str, speaker_segments: List[Dict] = None) -> Dict:
        """Gemini LLM 기반 분석"""
        # 텍스트 길이 제한 (토큰 절약)
        text = transcript[:3000] if len(transcript) > 3000 else transcript

        prompt = f"""다음은 초등학교 수업의 교사 발화 녹취록입니다. 교육학적 관점에서 분석해주세요.

발화 텍스트:
{text}

다음 항목을 JSON 형식으로 분석해주세요:
1. question_types: 질문 유형별 횟수 (open_ended: 개방형, closed: 폐쇄형, rhetorical: 수사적, scaffolding: 스캐폴딩)
2. feedback_quality: 피드백 유형별 횟수 (specific_praise: 구체적 칭찬, corrective: 교정적, generic: 일반적)
3. bloom_levels: Bloom 인지수준 비율 (remember, understand, apply, analyze, evaluate, create) 합계 1.0
4. interaction_score: 상호작용 품질 점수 (0-100)
5. key_observations: 주요 관찰 사항 (한국어, 3개)

JSON만 출력:"""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        text_resp = response.text.strip()

        # JSON 파싱
        import json
        # ```json ... ``` 블록 제거
        if "```" in text_resp:
            text_resp = re.sub(r'```(?:json)?\s*', '', text_resp)
            text_resp = text_resp.strip('` \n')

        result = json.loads(text_resp)

        # 필수 필드 보장
        return self._normalize_result(result)

    def _analyze_rules(self, transcript: str, segments: List[Dict] = None,
                       speaker_segments: List[Dict] = None) -> Dict:
        """규칙 기반 패턴 매칭 분석"""

        # 1. 질문 유형 분류
        question_types = self._classify_questions_rules(transcript)

        # 2. 피드백 품질 분석
        feedback_quality = self._classify_feedback_rules(transcript)

        # 3. Bloom 인지수준 추정
        bloom_levels = self._estimate_bloom_rules(transcript)

        # 4. 상호작용 점수
        interaction_score = self._calculate_interaction_score(
            question_types, feedback_quality, speaker_segments
        )

        return {
            "question_types": question_types,
            "feedback_quality": feedback_quality,
            "bloom_levels": bloom_levels,
            "interaction_score": round(interaction_score, 1),
            "key_observations": [],
            "analysis_method": "rules",
        }

    def _classify_questions_rules(self, text: str) -> Dict[str, int]:
        """규칙 기반 질문 유형 분류"""
        open_patterns = [
            r'왜\s', r'어떻게\s', r'어떤\s', r'무엇을', r'뭘\s',
            r'어떠한', r'어째서', r'생각[해하]', r'의견',
        ]
        closed_patterns = [
            r'맞[지죠나]', r'그렇[지죠]', r'[인은는이가]\s*거[죠지]',
            r'\d+[이가]\s*(맞|아닌)', r'알[겠았]',
        ]
        scaffolding_patterns = [
            r'힌트', r'다시\s*한번', r'차근차근', r'해볼[까래]',
            r'같이\s*(해|풀|생각)', r'도와[줄주]',
        ]
        rhetorical_patterns = [
            r'그렇[지죠]\s*[?？]?$', r'당연[하한]', r'물론',
        ]

        open_count = sum(len(re.findall(p, text)) for p in open_patterns)
        closed_count = sum(len(re.findall(p, text)) for p in closed_patterns)
        scaffolding_count = sum(len(re.findall(p, text)) for p in scaffolding_patterns)
        rhetorical_count = sum(len(re.findall(p, text)) for p in rhetorical_patterns)

        return {
            "open_ended": open_count,
            "closed": closed_count,
            "scaffolding": scaffolding_count,
            "rhetorical": rhetorical_count,
        }

    def _classify_feedback_rules(self, text: str) -> Dict[str, int]:
        """규칙 기반 피드백 유형 분류"""
        specific_praise_patterns = [
            r'잘\s*했', r'훌륭[해하한]', r'멋[지진져]',
            r'정확[해하한]', r'좋[은았]', r'대단[해하한]',
        ]
        corrective_patterns = [
            r'다시\s*한번', r'아니[야요]', r'틀[린렸]',
            r'고[쳐치]', r'주의[해하]', r'조심',
        ]
        generic_patterns = [
            r'그래[요]?$', r'네[에]?$', r'응[.?!]?$',
            r'좋아[요]?$', r'오케이',
        ]

        return {
            "specific_praise": sum(len(re.findall(p, text)) for p in specific_praise_patterns),
            "corrective": sum(len(re.findall(p, text)) for p in corrective_patterns),
            "generic": sum(len(re.findall(p, text)) for p in generic_patterns),
        }

    def _estimate_bloom_rules(self, text: str) -> Dict[str, float]:
        """Bloom 인지수준 규칙 기반 추정"""
        remember_kw = ['기억', '외워', '암기', '반복', '읽어']
        understand_kw = ['설명', '이해', '의미', '뜻', '왜냐하면', '때문']
        apply_kw = ['활용', '적용', '풀어', '계산', '사용', '해보']
        analyze_kw = ['비교', '차이', '분석', '관계', '원인', '구분']
        evaluate_kw = ['평가', '판단', '의견', '생각', '좋은', '나쁜']
        create_kw = ['만들', '설계', '창작', '발명', '새로운', '상상']

        counts = {
            "remember": sum(text.count(kw) for kw in remember_kw),
            "understand": sum(text.count(kw) for kw in understand_kw),
            "apply": sum(text.count(kw) for kw in apply_kw),
            "analyze": sum(text.count(kw) for kw in analyze_kw),
            "evaluate": sum(text.count(kw) for kw in evaluate_kw),
            "create": sum(text.count(kw) for kw in create_kw),
        }

        total = sum(counts.values()) or 1
        return {k: round(v / total, 2) for k, v in counts.items()}

    def _calculate_interaction_score(self, question_types: Dict,
                                     feedback_quality: Dict,
                                     speaker_segments: List[Dict] = None) -> float:
        """상호작용 품질 점수 (0-100)"""
        score = 50.0  # 기본점

        # 개방형 질문 비중
        total_q = sum(question_types.values()) or 1
        open_ratio = question_types.get("open_ended", 0) / total_q
        score += open_ratio * 20

        # 스캐폴딩 질문 보너스
        score += min(10, question_types.get("scaffolding", 0) * 3)

        # 구체적 칭찬
        score += min(10, feedback_quality.get("specific_praise", 0) * 2)

        # 교정 피드백
        score += min(5, feedback_quality.get("corrective", 0) * 1.5)

        # 화자 분리 데이터 활용
        if speaker_segments:
            student_turns = sum(1 for s in speaker_segments if s.get("speaker") == "student")
            score += min(10, student_turns * 1.5)

        return min(100, max(0, score))

    def _normalize_result(self, result: Dict) -> Dict:
        """LLM 결과 정규화"""
        defaults = self._empty_result()
        for key in defaults:
            if key not in result:
                result[key] = defaults[key]
        result["analysis_method"] = "llm"
        return result

    def _empty_result(self) -> Dict:
        """빈 결과"""
        return {
            "question_types": {"open_ended": 0, "closed": 0, "scaffolding": 0, "rhetorical": 0},
            "feedback_quality": {"specific_praise": 0, "corrective": 0, "generic": 0},
            "bloom_levels": {"remember": 0.3, "understand": 0.4, "apply": 0.2, "analyze": 0.1, "evaluate": 0, "create": 0},
            "interaction_score": 50.0,
            "key_observations": [],
            "analysis_method": "none",
        }
