import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import RealtimeFeedback from '../components/RealtimeFeedback'

describe('RealtimeFeedback 컴포넌트', () => {
    let mockWebSocket
    let onComplete
    let onError

    beforeEach(() => {
        vi.useFakeTimers({ shouldAdvanceTime: true })
        onComplete = vi.fn()
        onError = vi.fn()

        mockWebSocket = {
            onopen: null,
            onmessage: null,
            onclose: null,
            onerror: null,
            readyState: 1,
            send: vi.fn(),
            close: vi.fn()
        }

        global.WebSocket = vi.fn().mockImplementation((url) => {
            mockWebSocket.url = url
            setTimeout(() => mockWebSocket.onopen?.(), 10)
            return mockWebSocket
        })
    })

    afterEach(() => {
        vi.useRealTimers()
        vi.clearAllMocks()
    })

    describe('연결 상태', () => {
        it('연결 중 상태가 표시되어야 한다', () => {
            render(
                <RealtimeFeedback
                    analysisId="test-123"
                    onComplete={onComplete}
                    onError={onError}
                />
            )

            expect(screen.getByText('연결 중...')).toBeInTheDocument()
        })

        it('연결 성공 시 연결됨 상태가 표시되어야 한다', async () => {
            render(
                <RealtimeFeedback
                    analysisId="test-123"
                    onComplete={onComplete}
                    onError={onError}
                />
            )

            await act(async () => {
                await vi.advanceTimersByTimeAsync(50)
            })

            expect(screen.getByText('실시간 연결됨')).toBeInTheDocument()
        })
    })

    describe('진행률 표시', () => {
        it('진행률 업데이트가 반영되어야 한다', async () => {
            render(
                <RealtimeFeedback
                    analysisId="test-123"
                    onComplete={onComplete}
                    onError={onError}
                />
            )

            await act(async () => {
                await vi.advanceTimersByTimeAsync(50)
            })

            const progressMessage = {
                type: 'progress',
                overall_progress: 50,
                current_stage: { id: 'stt', name: '음성 인식', progress: 75 },
                stages: [
                    { id: 'upload', name: '업로드', status: 'completed' },
                    { id: 'stt', name: '음성 인식', status: 'in_progress' }
                ],
                elapsed_time: 30,
                timeline: [
                    { timestamp: new Date().toISOString(), message: 'STT 분석 중...' }
                ]
            }

            await act(async () => {
                mockWebSocket.onmessage({ data: JSON.stringify(progressMessage) })
            })

            expect(screen.getByText('50.0%')).toBeInTheDocument()
            expect(screen.getAllByText('음성 인식').length).toBeGreaterThan(0)
        })
    })

    describe('완료 처리', () => {
        it('완료 메시지 수신 시 onComplete 콜백이 호출되어야 한다', async () => {
            render(
                <RealtimeFeedback
                    analysisId="test-123"
                    onComplete={onComplete}
                    onError={onError}
                />
            )

            await act(async () => {
                await vi.advanceTimersByTimeAsync(50)
            })

            const completeMessage = {
                type: 'complete',
                elapsed_time: 120,
                result: { total_score: 85, grade: 'A' }
            }

            await act(async () => {
                mockWebSocket.onmessage({ data: JSON.stringify(completeMessage) })
            })

            expect(onComplete).toHaveBeenCalledWith({ total_score: 85, grade: 'A' })
            expect(screen.getByText(/분석이 완료되었습니다/i)).toBeInTheDocument()
        })
    })

    describe('에러 처리', () => {
        it('에러 메시지 수신 시 onError 콜백이 호출되어야 한다', async () => {
            render(
                <RealtimeFeedback
                    analysisId="test-123"
                    onComplete={onComplete}
                    onError={onError}
                />
            )

            await act(async () => {
                await vi.advanceTimersByTimeAsync(50)
            })

            const errorMessage = {
                type: 'error',
                message: '분석 중 오류가 발생했습니다.'
            }

            await act(async () => {
                mockWebSocket.onmessage({ data: JSON.stringify(errorMessage) })
            })

            expect(onError).toHaveBeenCalledWith('분석 중 오류가 발생했습니다.')
            expect(screen.getByText(/분석 중 오류가 발생했습니다/i)).toBeInTheDocument()
        })
    })

    describe('타임라인', () => {
        it('타임라인 이벤트가 표시되어야 한다', async () => {
            render(
                <RealtimeFeedback
                    analysisId="test-123"
                    onComplete={onComplete}
                    onError={onError}
                />
            )

            await act(async () => {
                await vi.advanceTimersByTimeAsync(50)
            })

            const progressMessage = {
                type: 'progress',
                overall_progress: 30,
                current_stage: { id: 'audio_extract', name: '오디오 추출', progress: 50 },
                stages: [],
                elapsed_time: 15,
                timeline: [
                    { timestamp: new Date().toISOString(), message: '오디오 추출 시작' }
                ]
            }

            await act(async () => {
                mockWebSocket.onmessage({ data: JSON.stringify(progressMessage) })
            })

            expect(screen.getByText('오디오 추출 시작')).toBeInTheDocument()
        })
    })

    describe('단계 표시', () => {
        it('분석 단계 목록이 표시되어야 한다', async () => {
            render(
                <RealtimeFeedback
                    analysisId="test-123"
                    onComplete={onComplete}
                    onError={onError}
                />
            )

            await act(async () => {
                await vi.advanceTimersByTimeAsync(50)
            })

            const progressMessage = {
                type: 'progress',
                overall_progress: 40,
                current_stage: { id: 'vision', name: '비전 분석', progress: 25 },
                stages: [
                    { id: 'upload', name: '업로드', status: 'completed' },
                    { id: 'audio_extract', name: '오디오 추출', status: 'completed' },
                    { id: 'stt', name: '음성 인식', status: 'completed' },
                    { id: 'vision', name: '비전 분석', status: 'in_progress' },
                    { id: 'vibe', name: '오디오 분석', status: 'pending' }
                ],
                elapsed_time: 45,
                timeline: []
            }

            await act(async () => {
                mockWebSocket.onmessage({ data: JSON.stringify(progressMessage) })
            })

            expect(screen.getByText('업로드')).toBeInTheDocument()
            expect(screen.getAllByText('비전 분석').length).toBeGreaterThan(0)
            expect(screen.getByText('오디오 분석')).toBeInTheDocument()
        })
    })

    describe('시간 표시', () => {
        it('경과 시간이 올바르게 포맷되어야 한다', async () => {
            render(
                <RealtimeFeedback
                    analysisId="test-123"
                    onComplete={onComplete}
                    onError={onError}
                />
            )

            await act(async () => {
                await vi.advanceTimersByTimeAsync(50)
            })

            const progressMessage = {
                type: 'progress',
                overall_progress: 50,
                current_stage: { id: 'stt', name: '음성 인식', progress: 50 },
                stages: [],
                elapsed_time: 125, // 2분 5초
                timeline: []
            }

            await act(async () => {
                mockWebSocket.onmessage({ data: JSON.stringify(progressMessage) })
            })

            expect(screen.getByText(/2:05/)).toBeInTheDocument()
        })
    })
})
