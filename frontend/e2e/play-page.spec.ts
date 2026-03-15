import { test, expect } from '@playwright/test'

test.describe('Play Page', () => {
  test('loads and displays game resources', async ({ page }) => {
    await page.goto('/play')
    // MiniCap has a "Resources" heading and resource names rendered
    await expect(page.getByText('Resources')).toBeVisible({ timeout: 10_000 })
    // The Resume/Pause button should be present
    await expect(page.getByRole('button', { name: /Resume|Pause/ })).toBeVisible()
  })

  test('displays generators section', async ({ page }) => {
    await page.goto('/play')
    await expect(page.getByText('Generators')).toBeVisible({ timeout: 10_000 })
  })

  test('has speed controls and auto-optimize button', async ({ page }) => {
    await page.goto('/play')
    await expect(page.getByRole('button', { name: 'Auto-Optimize' })).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole('button', { name: '1x' })).toBeVisible()
    await expect(page.getByRole('button', { name: '10x' })).toBeVisible()
    await expect(page.getByRole('button', { name: '100x' })).toBeVisible()
  })

  test('shows prestige panel for MiniCap', async ({ page }) => {
    await page.goto('/play')
    // Use the heading inside the prestige panel to avoid matching other elements
    await expect(page.getByRole('heading', { name: 'Prestige' })).toBeVisible({ timeout: 10_000 })
    // Also check the prestige button exists
    await expect(page.getByRole('button', { name: 'Prestige Now' })).toBeVisible()
  })

  test('can toggle pause/resume', async ({ page }) => {
    await page.goto('/play')
    const toggleButton = page.getByRole('button', { name: /Resume|Pause/ })
    await expect(toggleButton).toBeVisible({ timeout: 10_000 })

    // Click to start (Resume -> Pause)
    await toggleButton.click()
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible()

    // Click again to pause (Pause -> Resume)
    await page.getByRole('button', { name: 'Pause' }).click()
    await expect(page.getByRole('button', { name: 'Resume' })).toBeVisible()
  })
})
