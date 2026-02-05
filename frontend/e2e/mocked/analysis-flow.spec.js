// @ts-check
/**
 * GAIM Lab E2E Test - 분석 플로우 (Mocked API)
 * 
 * 🚨 핵심 전략: API Mocking으로 백엔드 없이 테스트
 * Dashboard.jsx 기준: 버튼='🚀 데모 실행', API 응답은 gaim_evaluation 중첩 구조
 */
import { test, expect } from '@playwright/test'
import { MOCK_DEMO_ANALYSIS } from '../../tests/fixtures/mock-data.js'

test.describe('GAIM Lab Analysis Flow (Mocked)', () => {

    test.beforeEach(async ({ page }) => {
        // 데모 분석 API Mock - POST 방식
        await page.route('**/api/v1/analysis/demo', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(MOCK_DEMO_ANALYSIS)
            })
        })
    })

    test('홈페이지(대시보드) 로드 및 타이틀 확인', async ({ page }) => {
        await page.goto('/')

        // 타이틀 확인 (index.html: "GAIM Lab - GINUE AI Microteaching Lab")
        await expect(page).toHaveTitle(/GAIM Lab/i)

        // 헤더 로고 확인
        await expect(page.locator('header h1')).toContainText('GAIM Lab')
    })

    test('네비게이션 링크 존재 확인', async ({ page }) => {
        await page.goto('/')

        // 네비게이션 링크 확인 (App.jsx의 <nav> 내부)
        const nav = page.locator('nav.nav')
        await expect(nav.getByRole('link', { name: '대시보드' })).toBeVisible()
        await expect(nav.getByRole('link', { name: '수업 분석' })).toBeVisible()
        await expect(nav.getByRole('link', { name: '포트폴리오' })).toBeVisible()
    })

    test('수업 분석 페이지 이동 및 업로드 영역 표시', async ({ page }) => {
        await page.goto('/upload')

        // 페이지 제목 확인
        await expect(page.locator('h1.page-title')).toContainText('수업 분석')

        // 업로드 영역 표시
        await expect(page.locator('.upload-zone')).toBeVisible()
        await expect(page.getByText('클릭하거나 영상 파일을 드래그하세요')).toBeVisible()
    })

    test('파일 선택 시 분석 버튼 표시', async ({ page }) => {
        await page.goto('/upload')

        // 파일 업로드 시뮬레이션
        const fileChooserPromise = page.waitForEvent('filechooser')
        await page.click('.upload-zone')
        const fileChooser = await fileChooserPromise

        await fileChooser.setFiles({
            name: 'test-lecture.mp4',
            mimeType: 'video/mp4',
            buffer: Buffer.from('fake video content for testing')
        })

        // 파일명 표시 확인
        await expect(page.getByText('test-lecture.mp4')).toBeVisible()

        // 분석 시작 버튼 확인
        await expect(page.getByRole('button', { name: /분석 시작/i })).toBeVisible()
    })

    test('대시보드에서 데모 실행 버튼 표시', async ({ page }) => {
        await page.goto('/')

        // 페이지 로드 대기
        await page.waitForLoadState('networkidle')

        // 데모 실행 버튼 확인 (Dashboard.jsx: '🚀 데모 실행')
        const demoButton = page.getByRole('button', { name: /데모 실행/i })
        await expect(demoButton).toBeVisible({ timeout: 10000 })
    })

    test('데모 실행 후 결과 표시', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')

        // 데모 실행 (버튼 텍스트: '🚀 데모 실행')
        await page.click('button:has-text("데모 실행")')

        // 결과 확인 - 타임아웃 증가 및 더 유연한 selector
        // gaim_evaluation.total_score=85, grade='A'
        await expect(page.locator('.score-value, .score-circle').first()).toBeVisible({ timeout: 10000 })
        await expect(page.getByText('85').first()).toBeVisible({ timeout: 5000 })
    })

    test('데모 실행 후 레이더 차트 렌더링', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')
        await page.click('button:has-text("데모 실행")')

        // Recharts 레이더 차트 렌더링 확인
        await expect(page.locator('.recharts-wrapper').first()).toBeVisible({ timeout: 10000 })
    })

    test('데모 실행 후 차원별 점수 표시', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')
        await page.click('button:has-text("데모 실행")')

        // 차원 테이블 또는 차원명 확인
        await expect(page.locator('.dimension-table, .dimension-row').first()).toBeVisible({ timeout: 10000 })
    })

    test('포트폴리오 페이지 접근', async ({ page }) => {
        await page.goto('/portfolio')
        await page.waitForLoadState('networkidle')

        // 포트폴리오 페이지 확인 - h1.page-title에 '포트폴리오' 텍스트
        await expect(page.locator('h1.page-title')).toContainText('포트폴리오')
    })
})
