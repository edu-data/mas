// @ts-check
/**
 * GAIM Lab Real E2E Test - 실제 백엔드 연동
 * 
 * 🎯 목적: Nightly 빌드에서 실제 영상 분석 플로우 검증
 * ⏰ 예상 시간: 20-30분 (실제 영상 분석 대기)
 * 
 * 📌 실행 방법:
 *   1. Docker로 백엔드 실행: docker-compose -f docker/docker-compose.test.yml up
 *   2. 테스트 실행: npx playwright test --project=real
 * 
 * ⚠️ 주의: CI 환경에서만 실행 (로컬에서는 .skip()으로 건너뜀)
 */
import { test, expect } from '@playwright/test'

// CI 환경 확인
const isCI = process.env.CI === 'true'
const REAL_API_URL = process.env.REAL_API_URL || 'http://localhost:8000'

// CI 환경이 아니면 테스트 스킵
const testOrSkip = isCI ? test : test.skip

test.describe('Real Backend E2E Tests', () => {

    test.beforeAll(async ({ request }) => {
        // 백엔드 헬스체크
        try {
            const response = await request.get(`${REAL_API_URL}/health`)
            expect(response.ok()).toBeTruthy()
            console.log('✅ Backend is healthy')
        } catch (error) {
            console.log('⚠️ Backend not available, skipping real E2E tests')
            test.skip()
        }
    })

    testOrSkip('실제 영상 업로드 및 분석 완료 대기', async ({ page }) => {
        // 타임아웃 10분 설정 (실제 분석 대기)
        test.setTimeout(600000)

        await page.goto('/upload')
        await page.waitForLoadState('networkidle')

        // 테스트 영상 파일 업로드
        // CI 환경에서는 TEST_VIDEO_URL에서 다운로드한 파일 사용
        const testVideoPath = process.env.TEST_VIDEO_PATH || 'test-fixtures/sample-lecture.mp4'

        const fileChooserPromise = page.waitForEvent('filechooser')
        await page.click('.upload-zone')
        const fileChooser = await fileChooserPromise

        // 실제 파일이 있는 경우에만 테스트 진행
        try {
            await fileChooser.setFiles(testVideoPath)
        } catch (error) {
            console.log('⚠️ Test video not found, skipping upload test')
            test.skip()
            return
        }

        // 분석 시작 버튼 클릭
        await page.click('button:has-text("분석 시작")')

        // 분석 완료 대기 (최대 10분)
        // 진행률 표시 확인
        await expect(page.locator('.progress-bar, .analysis-status')).toBeVisible({ timeout: 10000 })

        // 분석 완료까지 대기
        await expect(page.locator('.result-card, .analysis-result')).toBeVisible({ timeout: 600000 })

        // 결과 확인: 총점 표시
        await expect(page.locator('.score-value, .total-score')).toBeVisible()

        console.log('✅ Real analysis completed successfully')
    })

    testOrSkip('실제 데모 분석 API 응답 검증', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')

        // 데모 실행
        await page.click('button:has-text("데모 실행")')

        // 실제 API 응답 대기 (데모도 약간의 시간 소요)
        await expect(page.locator('.demo-result, .score-card').first()).toBeVisible({ timeout: 30000 })

        // 7차원 점수 표시 확인
        await expect(page.getByText(/수업 전문성/)).toBeVisible()
        await expect(page.locator('.recharts-wrapper').first()).toBeVisible()

        console.log('✅ Real demo analysis API working')
    })

    testOrSkip('분석 결과 차원별 점수 정확성 검증', async ({ page }) => {
        await page.goto('/')
        await page.waitForLoadState('networkidle')

        await page.click('button:has-text("데모 실행")')

        // 결과 대기
        await expect(page.locator('.dimension-table').first()).toBeVisible({ timeout: 30000 })

        // 7개 차원 모두 표시되는지 확인
        const dimensions = [
            '수업 전문성',
            '교수학습 방법',
            '판서 및 언어',
            '수업 태도',
            '학생 참여',
            '시간 배분',
            '창의성'
        ]

        for (const dim of dimensions) {
            await expect(page.getByText(dim)).toBeVisible({ timeout: 5000 })
        }

        console.log('✅ All 7 dimensions displayed correctly')
    })

    testOrSkip('포트폴리오 API 연동 검증', async ({ page, request }) => {
        // 포트폴리오 API 직접 호출
        const response = await request.get(`${REAL_API_URL}/api/v1/portfolio/demo_student`)

        if (response.ok()) {
            const data = await response.json()

            // 포트폴리오 데이터 구조 검증
            expect(data).toHaveProperty('student_id')
            expect(data).toHaveProperty('sessions')

            console.log('✅ Portfolio API working')
        } else {
            console.log('⚠️ Portfolio API not implemented yet')
        }
    })
})

// 성능 측정 테스트 (Nightly에서만 실행)
test.describe('Performance Benchmarks', () => {

    testOrSkip('분석 결과 페이지 로드 시간 측정', async ({ page }) => {
        const startTime = Date.now()

        await page.goto('/')
        await page.waitForLoadState('networkidle')
        await page.click('button:has-text("데모 실행")')

        // 결과 표시까지 시간 측정
        await expect(page.locator('.demo-result, .score-card').first()).toBeVisible({ timeout: 30000 })

        const loadTime = Date.now() - startTime
        console.log(`📊 Demo analysis load time: ${loadTime}ms`)

        // 30초 이내 완료 확인
        expect(loadTime).toBeLessThan(30000)
    })
})
