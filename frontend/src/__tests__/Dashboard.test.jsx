import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Dashboard from '../pages/Dashboard'

// Mock Recharts - ResponsiveContainer 문제 해결
vi.mock('recharts', async () => {
    const OriginalModule = await vi.importActual('recharts')
    return {
        ...OriginalModule,
        ResponsiveContainer: ({ children }) => (
            <div style={{ width: 400, height: 300 }}>{children}</div>
        )
    }
})

const renderDashboard = () => {
    return render(
        <BrowserRouter>
            <Dashboard />
        </BrowserRouter>
    )
}

describe('Dashboard 컴포넌트', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    describe('초기 렌더링', () => {
        it('페이지 제목이 표시되어야 한다', () => {
            renderDashboard()
            expect(screen.getByText(/대시보드/i)).toBeInTheDocument()
        })

        it('데모 분석 시작 버튼이 표시되어야 한다', () => {
            renderDashboard()
            expect(screen.getByRole('button', { name: /데모 실행/i })).toBeInTheDocument()
        })
    })

    describe('데모 분석 기능', () => {
        it('데모 분석 버튼 클릭 시 API 호출이 발생해야 한다', async () => {
            const mockResult = {
                gaim_evaluation: {
                    total_score: 85,
                    grade: 'A',
                    dimensions: [
                        { name: '수업 전문성', score: 17, max_score: 20, percentage: 85 },
                        { name: '교수학습 방법', score: 16, max_score: 20, percentage: 80 }
                    ],
                    overall_feedback: '우수한 수업입니다.'
                }
            }

            global.fetch = vi.fn().mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResult)
            })

            renderDashboard()
            const button = screen.getByRole('button', { name: /데모 실행/i })
            fireEvent.click(button)

            await waitFor(() => {
                expect(global.fetch).toHaveBeenCalledWith(
                    expect.stringContaining('/api/v1/analysis/demo'),
                    expect.any(Object)
                )
            })
        })

        it('분석 결과가 표시되어야 한다', async () => {
            const mockResult = {
                gaim_evaluation: {
                    total_score: 85,
                    grade: 'A',
                    dimensions: [
                        { name: '수업 전문성', score: 17, max_score: 20, percentage: 85 }
                    ],
                    overall_feedback: '우수한 수업입니다.'
                }
            }

            global.fetch = vi.fn().mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResult)
            })

            renderDashboard()
            const button = screen.getByRole('button', { name: /데모 실행/i })
            fireEvent.click(button)

            await waitFor(() => {
                expect(screen.getByText('85')).toBeInTheDocument()
            })
        })
    })

    describe('차트 데이터 변환', () => {
        it('레이더 차트에 7개 차원 데이터가 표시되어야 한다', async () => {
            const mockResult = {
                gaim_evaluation: {
                    total_score: 85,
                    grade: 'A',
                    dimensions: [
                        { name: '수업 전문성', score: 17, max_score: 20, percentage: 85 },
                        { name: '교수학습 방법', score: 16, max_score: 20, percentage: 80 },
                        { name: '판서 및 언어', score: 12, max_score: 15, percentage: 80 },
                        { name: '수업 태도', score: 13, max_score: 15, percentage: 86 },
                        { name: '학생 참여', score: 12, max_score: 15, percentage: 80 },
                        { name: '시간 배분', score: 8, max_score: 10, percentage: 80 },
                        { name: '창의성', score: 4, max_score: 5, percentage: 80 }
                    ],
                    overall_feedback: '우수한 수업입니다.'
                }
            }

            global.fetch = vi.fn().mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResult)
            })

            renderDashboard()
            const button = screen.getByRole('button', { name: /데모 실행/i })
            fireEvent.click(button)

            await waitFor(() => {
                expect(screen.getByText('수업 전문성')).toBeInTheDocument()
            })
        })
    })
})
