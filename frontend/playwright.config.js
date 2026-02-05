import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: [
        ['html'],
        ['list']
    ],

    use: {
        baseURL: 'http://localhost:5173',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
        video: 'retain-on-failure'
    },

    // 🚨 핵심: 3개 프로젝트 분리 (mocked / real / visual)
    projects: [
        // Fast Track: API Mocking으로 초고속 테스트 (PR 시 실행)
        {
            name: 'mocked',
            testDir: './e2e/mocked',
            use: { ...devices['Desktop Chrome'] }
        },

        // Slow Track: 실제 서버 연동 테스트 (Nightly 실행)
        {
            name: 'real',
            testDir: './e2e/real',
            timeout: 600_000, // 10분 (대용량 분석 대기)
            use: {
                ...devices['Desktop Chrome'],
                baseURL: process.env.REAL_API_URL || 'http://localhost:8000'
            }
        },

        // Visual Regression: 스크린샷 비교 테스트
        {
            name: 'visual',
            testDir: './e2e/visual',
            use: { ...devices['Desktop Chrome'] },
            // 스냅샷 저장 위치
            snapshotDir: './e2e/visual/__snapshots__'
        },

        // 기존 호환용: 레거시 테스트
        {
            name: 'legacy',
            testDir: './e2e',
            testIgnore: ['**/mocked/**', '**/real/**', '**/visual/**'],
            use: { ...devices['Desktop Chrome'] }
        }
    ],

    webServer: {
        command: 'npm run dev',
        url: 'http://localhost:5173',
        reuseExistingServer: !process.env.CI,
        timeout: 120 * 1000
    }
})
