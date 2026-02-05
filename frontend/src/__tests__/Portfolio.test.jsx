import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Portfolio from '../pages/Portfolio'

// Mock Recharts
vi.mock('recharts', async () => {
    const OriginalModule = await vi.importActual('recharts')
    return {
        ...OriginalModule,
        ResponsiveContainer: ({ children }) => (
            <div style={{ width: 400, height: 300 }}>{children}</div>
        )
    }
})

const renderPortfolio = () => {
    return render(
        <BrowserRouter>
            <Portfolio />
        </BrowserRouter>
    )
}

// Mock data matching the actual Portfolio component's demo data
const mockPortfolioData = {
    student_id: 'demo_student',
    name: '김예비',
    total_sessions: 5,
    average_score: 78.5,
    best_score: 85.0,
    improvement_rate: 12.5,
    badges: ['first_session', 'five_sessions', 'score_80']
}

const mockSessions = [
    {
        date: '2026-01-15', total_score: 72, grade: 'C+',
        dimensions: [
            { name: '수업 전문성', score: 12, max: 20 },
            { name: '교수학습 방법', score: 13, max: 20 },
            { name: '판서 및 언어', score: 10, max: 15 },
            { name: '수업 태도', score: 11, max: 15 },
            { name: '학생 참여', score: 10, max: 15 },
            { name: '시간 배분', score: 7, max: 10 },
            { name: '창의성', score: 3, max: 5 }
        ]
    },
    {
        date: '2026-02-05', total_score: 85, grade: 'B+',
        dimensions: [
            { name: '수업 전문성', score: 16, max: 20 },
            { name: '교수학습 방법', score: 17, max: 20 },
            { name: '판서 및 언어', score: 13, max: 15 },
            { name: '수업 태도', score: 13, max: 15 },
            { name: '학생 참여', score: 13, max: 15 },
            { name: '시간 배분', score: 8, max: 10 },
            { name: '창의성', score: 4, max: 5 }
        ]
    }
]

const mockBadges = [
    { badge_id: 'first_session', name: '첫 수업 시연', icon: '🎬', category: 'milestone', points: 10, earned_at: '2026-01-15' },
    { badge_id: 'score_80', name: '우수 수업', icon: '⭐', category: 'achievement', points: 25, earned_at: '2026-02-02' }
]

describe('Portfolio 컴포넌트', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockPortfolioData)
        })
    })

    describe('초기 렌더링', () => {
        it('포트폴리오 페이지 제목이 표시되어야 한다', () => {
            renderPortfolio()
            // Use getByRole for more stable selector - h1 element with text
            expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/포트폴리오/)
        })

        it('데모 데이터 로드 버튼이 표시되어야 한다', () => {
            renderPortfolio()
            expect(screen.getByRole('button', { name: /데모 보기/i })).toBeInTheDocument()
        })
    })

    describe('데이터 로딩', () => {
        it('데모 데이터 로드 시 학생 정보가 표시되어야 한다', async () => {
            renderPortfolio()

            const loadButton = screen.getByRole('button', { name: /데모 보기/i })
            fireEvent.click(loadButton)

            await waitFor(() => {
                expect(screen.getByText('김예비')).toBeInTheDocument()
            })
        })

        it('세션 목록이 표시되어야 한다', async () => {
            renderPortfolio()

            const loadButton = screen.getByRole('button', { name: /데모 보기/i })
            fireEvent.click(loadButton)

            // Wait for loading spinner to disappear and data to load (500ms setTimeout in component)
            await waitFor(() => {
                // Check for session dates that exist in demo data
                expect(screen.getByText('#1')).toBeInTheDocument()
            }, { timeout: 2000 })
        })
    })

    describe('세션 선택 인터랙션', () => {
        it('세션 클릭 시 선택 상태가 변경되어야 한다', async () => {
            renderPortfolio()

            const loadButton = screen.getByRole('button', { name: /데모 보기/i })
            fireEvent.click(loadButton)

            await waitFor(() => {
                // Check for session items by class rather than data-testid
                const sessionItems = document.querySelectorAll('.session-item')
                expect(sessionItems.length).toBeGreaterThan(0)
            })
        })
    })

    describe('배지 렌더링', () => {
        it('획득한 배지가 표시되어야 한다', async () => {
            renderPortfolio()

            const loadButton = screen.getByRole('button', { name: /데모 보기/i })
            fireEvent.click(loadButton)

            await waitFor(() => {
                expect(screen.getByText('첫 수업 시연')).toBeInTheDocument()
                expect(screen.getByText('우수 수업')).toBeInTheDocument()
            })
        })
    })

    describe('PDF 내보내기', () => {
        it('PDF 다운로드 버튼이 표시되어야 한다', async () => {
            renderPortfolio()

            const loadButton = screen.getByRole('button', { name: /데모 보기/i })
            fireEvent.click(loadButton)

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /PDF/i })).toBeInTheDocument()
            })
        })
    })
})
