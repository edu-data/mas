/**
 * GAIM Lab Mock Data Package
 * 
 * 다양한 분석 상태와 결과를 시뮬레이션하기 위한 Mock 데이터 모음
 * 프론트엔드 개발자가 백엔드 없이도 개발/테스트 가능
 */

// ==================== 분석 상태 Mock ====================

/** 분석 완료 상태 (성공 케이스) */
export const MOCK_ANALYSIS_COMPLETED = {
    status: 'COMPLETED',
    progress: 100,
    result: {
        total_score: 85,
        grade: 'A',
        death_valley: [
            { start: 120, end: 140 },  // 2분~2분20초
            { start: 420, end: 450 }   // 7분~7분30초
        ],
        dimensions: [
            { name: '수업 전문성', score: 17, max_score: 20, percentage: 85 },
            { name: '교수학습 방법', score: 16, max_score: 20, percentage: 80 },
            { name: '판서 및 언어', score: 12, max_score: 15, percentage: 80 },
            { name: '수업 태도', score: 13, max_score: 15, percentage: 87 },
            { name: '학생 참여', score: 12, max_score: 15, percentage: 80 },
            { name: '시간 배분', score: 9, max_score: 10, percentage: 90 },
            { name: '창의성', score: 4, max_score: 5, percentage: 80 }
        ],
        strengths: [
            '학생들과의 시선 교환이 자연스럽습니다',
            '목소리 톤이 일정하게 유지됩니다',
            '핵심 개념 설명이 명확합니다'
        ],
        improvements: [
            '2분~2분20초 구간에서 에너지가 감소합니다',
            '제스처 활용도를 높이면 좋겠습니다'
        ],
        overall_feedback: '전반적으로 우수한 수업입니다. 학생 참여를 더 유도하면 완벽할 것입니다.'
    }
}

/** 분석 진행 중 상태 */
export const MOCK_ANALYSIS_PROCESSING = {
    status: 'PROCESSING',
    progress: 45,
    current_step: 'vision_analysis',
    estimated_remaining: 120 // 초
}

/** 분석 실패 상태 */
export const MOCK_ANALYSIS_FAILED = {
    status: 'FAILED',
    error: '영상 파일을 처리할 수 없습니다. 지원되는 형식: MP4, MOV, AVI',
    error_code: 'INVALID_VIDEO_FORMAT'
}

/** 저조한 결과 (개선 필요 케이스) */
export const MOCK_ANALYSIS_BAD_RESULT = {
    status: 'COMPLETED',
    progress: 100,
    result: {
        total_score: 58,
        grade: 'C',
        death_valley: [
            { start: 60, end: 180 },   // 1분~3분
            { start: 300, end: 400 },  // 5분~6분40초
            { start: 540, end: 600 }   // 9분~10분
        ],
        dimensions: [
            { name: '수업 전문성', score: 12, max_score: 20, percentage: 60 },
            { name: '교수학습 방법', score: 10, max_score: 20, percentage: 50 },
            { name: '판서 및 언어', score: 9, max_score: 15, percentage: 60 },
            { name: '수업 태도', score: 8, max_score: 15, percentage: 53 },
            { name: '학생 참여', score: 8, max_score: 15, percentage: 53 },
            { name: '시간 배분', score: 7, max_score: 10, percentage: 70 },
            { name: '창의성', score: 2, max_score: 5, percentage: 40 }
        ],
        strengths: [
            '시간 배분이 비교적 적절합니다'
        ],
        improvements: [
            '학생들과의 시선 교환이 부족합니다',
            '목소리 에너지가 전반적으로 낮습니다',
            '제스처 활용이 거의 없습니다',
            '발문 빈도를 높여 학생 참여를 유도하세요'
        ],
        overall_feedback: '개선이 필요한 부분이 많습니다. 멘토와 상담을 권장합니다.'
    }
}

// ==================== 데모 분석 Mock ====================

// Dashboard.jsx에서 data.gaim_evaluation으로 접근하므로 중첩 구조 필요
export const MOCK_DEMO_ANALYSIS = {
    gaim_evaluation: {
        total_score: 85,
        grade: 'A',
        dimensions: [
            { name: '수업 전문성', score: 17, max_score: 20, percentage: 85, criteria: {} },
            { name: '교수학습 방법', score: 16, max_score: 20, percentage: 80, criteria: {} },
            { name: '판서 및 언어', score: 12, max_score: 15, percentage: 80, criteria: {} },
            { name: '수업 태도', score: 13, max_score: 15, percentage: 86, criteria: {} },
            { name: '학생 참여', score: 12, max_score: 15, percentage: 80, criteria: {} },
            { name: '시간 배분', score: 8, max_score: 10, percentage: 80, criteria: {} },
            { name: '창의성', score: 4, max_score: 5, percentage: 80, criteria: {} }
        ],
        strengths: ['시선 교환이 자연스럽습니다'],
        improvements: ['제스처 활용도를 높이세요'],
        overall_feedback: '전반적으로 우수한 수업입니다.'
    }
}

// ==================== 포트폴리오 Mock ====================

export const MOCK_PORTFOLIO = {
    student: {
        id: 'student-001',
        name: '김예비',
        email: 'kim@example.com',
        created_at: '2025-09-01'
    },
    sessions: [
        {
            id: 'session-1',
            date: '2026-01-15',
            total_score: 72,
            grade: 'B'
        },
        {
            id: 'session-2',
            date: '2026-01-22',
            total_score: 78,
            grade: 'B+'
        },
        {
            id: 'session-3',
            date: '2026-01-29',
            total_score: 85,
            grade: 'A'
        }
    ],
    badges: [
        { id: 'first-lesson', name: '첫 수업 시연', earned_at: '2026-01-15', type: 'milestone' },
        { id: 'growth-streak', name: '연속 성장', earned_at: '2026-01-29', type: 'achievement' }
    ],
    growth_trend: 'positive',
    dimension_comparison: [
        { dimension: '수업 전문성', session1: 14, session2: 15, session3: 17 },
        { dimension: '교수학습 방법', session1: 12, session2: 14, session3: 16 },
        { dimension: '판서 및 언어', session1: 10, session2: 11, session3: 12 },
        { dimension: '수업 태도', session1: 10, session2: 12, session3: 13 },
        { dimension: '학생 참여', session1: 9, session2: 10, session3: 12 },
        { dimension: '시간 배분', session1: 7, session2: 8, session3: 9 },
        { dimension: '창의성', session1: 2, session2: 3, session3: 4 }
    ]
}

// ==================== WebSocket 메시지 Mock ====================

export const MOCK_WS_MESSAGES = {
    progress: (percent, step = 'processing') => ({
        type: 'progress',
        data: {
            progress: percent,
            current_step: step,
            message: `분석 진행 중... ${percent}%`
        }
    }),

    complete: (result = MOCK_ANALYSIS_COMPLETED.result) => ({
        type: 'complete',
        data: result
    }),

    error: (message = '분석 중 오류가 발생했습니다') => ({
        type: 'error',
        data: { message }
    })
}

// ==================== 타임라인 마커 Mock ====================

export const MOCK_TIMELINE_MARKERS = [
    { time: 0, label: '수업 시작', type: 'event' },
    { time: 120, label: '죽음의 구간', type: 'warning' },
    { time: 300, label: '핵심 개념 설명', type: 'highlight' },
    { time: 420, label: '에너지 저하', type: 'warning' },
    { time: 600, label: '마무리', type: 'event' }
]
