// @ts-check
import { test, expect } from '@playwright/test'

test.describe('포트폴리오 관리', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/')
        await page.click('text=포트폴리오')
    })

    test('포트폴리오 페이지가 로드되어야 한다', async ({ page }) => {
        await expect(page.locator('h1')).toContainText('포트폴리오')
    })

    test('데모 데이터 로드 버튼이 표시되어야 한다', async ({ page }) => {
        const loadButton = page.getByRole('button', { name: /데모 데이터/i })
        await expect(loadButton).toBeVisible()
    })

    test('데모 데이터 로드 시 학생 정보가 표시되어야 한다', async ({ page }) => {
        await page.click('button:has-text("데모 데이터")')

        // 학생 정보 카드 확인
        await expect(page.locator('.student-info')).toBeVisible({ timeout: 5000 })
    })

    test('세션 목록이 표시되어야 한다', async ({ page }) => {
        await page.click('button:has-text("데모 데이터")')

        // 세션 목록 로딩 대기
        await expect(page.locator('.session-list')).toBeVisible({ timeout: 5000 })
    })

    test('세션 클릭 시 상세 정보가 업데이트되어야 한다', async ({ page }) => {
        await page.click('button:has-text("데모 데이터")')

        // 세션 목록 로딩 대기
        await page.waitForSelector('.session-item', { timeout: 5000 })

        // 첫 번째 세션 클릭
        await page.click('.session-item:first-child')

        // 레이더 차트 영역 업데이트 확인
        await expect(page.locator('.dimension-chart')).toBeVisible()
    })

    test('배지가 표시되어야 한다', async ({ page }) => {
        await page.click('button:has-text("데모 데이터")')

        // 배지 섹션 확인
        await expect(page.locator('.badges-section')).toBeVisible({ timeout: 5000 })
    })

    test('PDF 내보내기 버튼이 동작해야 한다', async ({ page }) => {
        await page.click('button:has-text("데모 데이터")')

        // PDF 버튼 찾기
        const pdfButton = page.getByRole('button', { name: /PDF/i })
        await expect(pdfButton).toBeVisible({ timeout: 5000 })

        // 클릭 가능 확인
        await expect(pdfButton).toBeEnabled()
    })
})

test.describe('포트폴리오 차트', () => {
    test('점수 추이 차트가 표시되어야 한다', async ({ page }) => {
        await page.goto('/')
        await page.click('text=포트폴리오')
        await page.click('button:has-text("데모 데이터")')

        // 라인 차트 영역 확인
        await expect(page.locator('.progress-chart')).toBeVisible({ timeout: 5000 })
    })

    test('차원별 비교 차트가 표시되어야 한다', async ({ page }) => {
        await page.goto('/')
        await page.click('text=포트폴리오')
        await page.click('button:has-text("데모 데이터")')

        // 바 차트 또는 레이더 차트 영역 확인
        await expect(page.locator('.comparison-chart, .dimension-chart')).toBeVisible({ timeout: 5000 })
    })
})
