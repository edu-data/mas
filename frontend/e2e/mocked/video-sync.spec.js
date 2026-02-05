// @ts-check
/**
 * GAIM Lab E2E Test - Video-Chart 동기화 및 대시보드 상호작용
 * 
 * 🎯 핵심 검증: 대시보드 및 차트 렌더링 테스트
 * Dashboard.jsx 기준: 버튼='🚀 데모 실행', gaim_evaluation 중첩 구조
 */
import { test, expect } from '@playwright/test'
import { MOCK_DEMO_ANALYSIS } from '../../tests/fixtures/mock-data.js'

test.describe('Video-Chart Synchronization (Mocked)', () => {

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

    test('대시보드 데모 실행 후 차트가 렌더링됨', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')

        // 데모 실행 (버튼 텍스트: '🚀 데모 실행')
        await page.click('button:has-text("데모 실행")')

        // 레이더 차트 렌더링 대기 - 타임아웃 증가
        const chart = page.locator('.recharts-wrapper')
        await expect(chart.first()).toBeVisible({ timeout: 15000 })
    })

    test('대시보드에서 7차원 점수가 표시됨', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')
        await page.click('button:has-text("데모 실행")')

        // 결과 영역이 나타날 때까지 대기
        await expect(page.locator('.demo-result, .score-card').first()).toBeVisible({ timeout: 10000 })

        // 총점 표시 확인 (85)
        await expect(page.getByText('85').first()).toBeVisible({ timeout: 5000 })
    })

    test('대시보드 차원별 차트가 렌더링됨', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')
        await page.click('button:has-text("데모 실행")')

        // 차트 컨테이너 확인 - 타임아웃 증가
        await expect(page.locator('.recharts-wrapper').first()).toBeVisible({ timeout: 15000 })

        // 차원 테이블 또는 차원명 텍스트 확인
        await expect(page.locator('.dimension-table, .dimension-row').first()).toBeVisible({ timeout: 10000 })
    })

    test('업로드 페이지 업로드 영역 동작', async ({ page }) => {
        await page.goto('/upload')

        // 업로드 영역 표시 확인
        const uploadZone = page.locator('.upload-zone')
        await expect(uploadZone).toBeVisible()

        // 드래그 오버 이벤트 테스트
        await uploadZone.dispatchEvent('dragover')
    })

    test('업로드 페이지 파일 선택 후 상태 변경', async ({ page }) => {
        await page.goto('/upload')

        // 파일 업로드
        const fileChooserPromise = page.waitForEvent('filechooser')
        await page.click('.upload-zone')
        const fileChooser = await fileChooserPromise

        await fileChooser.setFiles({
            name: 'test.mp4',
            mimeType: 'video/mp4',
            buffer: Buffer.from('test content')
        })

        // 파일 정보 표시 확인
        await expect(page.getByText('test.mp4')).toBeVisible()

        // 업로드 영역이 has-file 클래스를 갖게 됨
        await expect(page.locator('.upload-zone.has-file')).toBeVisible()
    })
})
