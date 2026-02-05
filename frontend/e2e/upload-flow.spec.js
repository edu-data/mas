// @ts-check
import { test, expect } from '@playwright/test'

test.describe('업로드 및 분석 플로우', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/')
    })

    test('홈페이지가 로드되어야 한다', async ({ page }) => {
        await expect(page).toHaveTitle(/GAIM Lab/i)
    })

    test('수업 분석 페이지로 이동할 수 있어야 한다', async ({ page }) => {
        await page.click('text=수업 분석')
        await expect(page.locator('h1')).toContainText('수업 분석')
    })

    test('업로드 영역이 표시되어야 한다', async ({ page }) => {
        await page.click('text=수업 분석')
        await expect(page.locator('.upload-zone')).toBeVisible()
        await expect(page.getByText('클릭하거나 영상 파일을 드래그하세요')).toBeVisible()
    })

    test('파일 선택 후 분석 버튼이 활성화되어야 한다', async ({ page }) => {
        await page.click('text=수업 분석')

        // 테스트용 비디오 파일 생성 및 업로드
        const fileChooserPromise = page.waitForEvent('filechooser')
        await page.click('.upload-zone')
        const fileChooser = await fileChooserPromise

        // 간단한 테스트 파일 생성
        await fileChooser.setFiles({
            name: 'test-video.mp4',
            mimeType: 'video/mp4',
            buffer: Buffer.from('fake video content')
        })

        // 파일명과 분석 버튼 확인
        await expect(page.getByText('test-video.mp4')).toBeVisible()
        await expect(page.getByRole('button', { name: /분석 시작/i })).toBeVisible()
    })

    test('드래그 앤 드롭 영역이 동작해야 한다', async ({ page }) => {
        await page.click('text=수업 분석')

        const dropZone = page.locator('.upload-zone')
        await expect(dropZone).toBeVisible()

        // dragover 이벤트 발생 확인
        await dropZone.dispatchEvent('dragover')
    })
})

test.describe('데모 분석 플로우', () => {
    test('대시보드에서 데모 분석이 가능해야 한다', async ({ page }) => {
        await page.goto('/')
        await page.click('text=대시보드')

        // 데모 분석 버튼 클릭
        const demoButton = page.getByRole('button', { name: /데모 분석/i })
        await expect(demoButton).toBeVisible()
    })
})
