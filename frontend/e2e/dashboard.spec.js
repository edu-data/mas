// @ts-check
import { test, expect } from '@playwright/test'

test.describe('대시보드', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/')
        await page.click('text=대시보드')
    })

    test('대시보드 페이지가 로드되어야 한다', async ({ page }) => {
        await expect(page.locator('h1')).toContainText('대시보드')
    })

    test('데모 분석 버튼이 표시되어야 한다', async ({ page }) => {
        const demoButton = page.getByRole('button', { name: /데모 분석/i })
        await expect(demoButton).toBeVisible()
    })

    test('데모 분석 실행 시 결과가 표시되어야 한다', async ({ page }) => {
        // Mock API 응답
        await page.route('**/api/v1/analysis/demo', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
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
                    overall_feedback: '전반적으로 우수한 수업입니다.'
                })
            })
        })

        // 데모 분석 버튼 클릭
        await page.click('button:has-text("데모 분석")')

        // 결과 표시 확인
        await expect(page.getByText('85')).toBeVisible({ timeout: 5000 })
        await expect(page.getByText('A')).toBeVisible()
    })

    test('7차원 평가 테이블이 표시되어야 한다', async ({ page }) => {
        // Mock API 응답
        await page.route('**/api/v1/analysis/demo', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    total_score: 85,
                    grade: 'A',
                    dimensions: [
                        { name: '수업 전문성', score: 17, max_score: 20, percentage: 85 }
                    ],
                    overall_feedback: '우수합니다.'
                })
            })
        })

        await page.click('button:has-text("데모 분석")')

        // 차원별 테이블 또는 차트 확인
        await expect(page.locator('.dimension-table, .dimension-chart')).toBeVisible({ timeout: 5000 })
    })

    test('레이더 차트가 렌더링되어야 한다', async ({ page }) => {
        // Mock API 응답
        await page.route('**/api/v1/analysis/demo', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    total_score: 85,
                    grade: 'A',
                    dimensions: [
                        { name: '수업 전문성', score: 17, max_score: 20, percentage: 85 },
                        { name: '교수학습 방법', score: 16, max_score: 20, percentage: 80 }
                    ],
                    overall_feedback: '우수합니다.'
                })
            })
        })

        await page.click('button:has-text("데모 분석")')

        // Recharts 렌더링 확인 (SVG 요소)
        await expect(page.locator('.recharts-wrapper')).toBeVisible({ timeout: 5000 })
    })
})

test.describe('대시보드 네비게이션', () => {
    test('메인 네비게이션이 동작해야 한다', async ({ page }) => {
        await page.goto('/')

        // 대시보드 링크 클릭
        await page.click('text=대시보드')
        await expect(page).toHaveURL(/.*dashboard/i)

        // 포트폴리오로 이동
        await page.click('text=포트폴리오')
        await expect(page).toHaveURL(/.*portfolio/i)

        // 수업 분석으로 이동
        await page.click('text=수업 분석')
        await expect(page).toHaveURL(/.*upload/i)
    })
})
