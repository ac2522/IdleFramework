import { test, expect } from '@playwright/test'

test.describe('Analyze Page', () => {
  test('displays analysis controls', async ({ page }) => {
    await page.goto('/analyze')
    await expect(page.getByText('Game Analysis')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Analysis Controls')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Run Analysis' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Compare Free vs Paid' })).toBeVisible()
  })

  test('can run analysis on MiniCap', async ({ page }) => {
    await page.goto('/analyze')
    await expect(page.getByRole('button', { name: 'Run Analysis' })).toBeVisible({ timeout: 10_000 })

    await page.getByRole('button', { name: 'Run Analysis' }).click()

    // Should show loading spinner then results
    await expect(page.getByText('Summary')).toBeVisible({ timeout: 30_000 })
  })
})
