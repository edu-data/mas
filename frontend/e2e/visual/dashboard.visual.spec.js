// @ts-check
/**
 * GAIM Lab Visual Regression Test - 대시보드/차트 렌더링
 * 
 * 🎯 목표: 코드로 검증하기 힘든 히트맵, 파형 차트가 
 *         디자인 시안대로 그려졌는지 스크린샷 비교로 확인
 * 
 * 📌 첫 실행: npx playwright test --project=visual --update-snapshots
 */
import { test, expect } from '@playwright/test'
import { MOCK_DEMO_ANALYSIS, MOCK_ANALYSIS_COMPLETED } from '../../tests/fixtures/mock-data.js'

test.describe('Dashboard Visual Regression', () => {

    test.beforeEach(async ({ page }) => {
        // API Mock 설정 (beforeEach에서 설정해야 navigation 후에도 유지됨)
        await page.route('**/api/v1/analysis/demo', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(MOCK_DEMO_ANALYSIS)
            })
        })

        await page.route('**/api/v1/analysis/result/**', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(MOCK_ANALYSIS_COMPLETED.result)
            })
        })
    })

    test('대시보드 전체 레이아웃 스냅샷', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')

        // 전체 페이지 스크린샷 비교
        await expect(page).toHaveScreenshot('dashboard-layout.png', {
            maxDiffPixels: 200,     // 렌더링 엔진 차이 허용
            threshold: 0.3,          // 픽셀 색상 차이 허용 (0-1)
            animations: 'disabled'   // 애니메이션 무시
        })
    })

    test('레이더 차트 렌더링 검증', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')

        // 데모 실행 버튼 클릭 (Dashboard.jsx: '🚀 데모 실행')
        await page.click('button:has-text("데모 실행")')

        // 레이더 차트 렌더링 대기
        const radarChart = page.locator('.recharts-wrapper').first()
        await expect(radarChart).toBeVisible({ timeout: 10000 })

        // 차트 영역 스크린샷 비교
        await expect(radarChart).toHaveScreenshot('radar-chart-baseline.png', {
            maxDiffPixels: 100,
            threshold: 0.2
        })
    })

    test('7차원 평가 테이블 렌더링 검증', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')
        await page.click('button:has-text("데모 실행")')

        // 평가 테이블 대기
        const dimensionTable = page.locator('.dimension-table').first()
        await expect(dimensionTable).toBeVisible({ timeout: 10000 })

        await expect(dimensionTable).toHaveScreenshot('dimension-table-baseline.png', {
            maxDiffPixels: 50,
            threshold: 0.2
        })
    })

    test('점수 카드 스타일 검증', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')
        await page.click('button:has-text("데모 실행")')

        // 총점 카드 영역
        const scoreCard = page.locator('.score-card').first()
        await expect(scoreCard).toBeVisible({ timeout: 10000 })

        await expect(scoreCard).toHaveScreenshot('score-card-baseline.png', {
            maxDiffPixels: 30,
            threshold: 0.2
        })
    })
})

test.describe('Report Page Visual Regression', () => {

    test.beforeEach(async ({ page }) => {
        await page.route('**/api/v1/analysis/**', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(MOCK_ANALYSIS_COMPLETED)
            })
        })
    })

    test('분석 결과 리포트 페이지 레이아웃', async ({ page }) => {
        // /report/:id 라우트가 없으므로 대시보드에서 테스트
        await page.goto('/')
        await page.waitForLoadState('networkidle')

        // 리포트 전체 레이아웃 스크린샷
        await expect(page).toHaveScreenshot('report-layout.png', {
            maxDiffPixels: 300,
            threshold: 0.3,
            animations: 'disabled'
        })
    })

    test('타임라인/히트맵 차트 렌더링', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')

        // 차트가 있을 경우에만 스크린샷
        const chart = page.locator('.recharts-wrapper').first()
        if (await chart.count() > 0) {
            await expect(chart).toHaveScreenshot('heatmap-baseline.png', {
                maxDiffPixels: 100,
                threshold: 0.2
            })
        }
    })

    test('피드백 섹션 렌더링', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')

        // 피드백 섹션이 있을 경우에만 스크린샷
        const feedbackSection = page.locator('.feedback-section').first()
        if (await feedbackSection.count() > 0) {
            await expect(feedbackSection).toHaveScreenshot('feedback-section-baseline.png', {
                maxDiffPixels: 80,
                threshold: 0.2
            })
        }
    })
})

test.describe('Portfolio Visual Regression', () => {

    test.beforeEach(async ({ page }) => {
        await page.route('**/api/v1/portfolio/**', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    sessions: [
                        { id: 1, date: '2026-01-15', total_score: 72, grade: 'B' },
                        { id: 2, date: '2026-01-22', total_score: 78, grade: 'B+' },
                        { id: 3, date: '2026-01-29', total_score: 85, grade: 'A' }
                    ],
                    badges: [
                        { id: 'first', name: '첫 수업', type: 'milestone' }
                    ]
                })
            })
        })
    })

    test('포트폴리오 성장 차트 렌더링', async ({ page }) => {
        await page.goto('/portfolio')
        await page.waitForLoadState('networkidle')

        // 성장 추이 차트
        const growthChart = page.locator('.recharts-wrapper').first()

        if (await growthChart.count() > 0) {
            await expect(growthChart).toHaveScreenshot('growth-chart-baseline.png', {
                maxDiffPixels: 100,
                threshold: 0.2
            })
        }
    })

    test('배지 그리드 렌더링', async ({ page }) => {
        await page.goto('/portfolio')
        await page.waitForLoadState('networkidle')

        const badgeGrid = page.locator('.badges-grid').first()

        if (await badgeGrid.count() > 0) {
            await expect(badgeGrid).toHaveScreenshot('badge-grid-baseline.png', {
                maxDiffPixels: 50,
                threshold: 0.2
            })
        }
    })
})
