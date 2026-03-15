import { test, expect } from '@playwright/test'

test.describe('Editor Page', () => {
  test('loads the node editor canvas', async ({ page }) => {
    await page.goto('/editor')
    await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10_000 })
  })

  test('displays the node palette', async ({ page }) => {
    await page.goto('/editor')
    await expect(page.getByText('Node Palette')).toBeVisible({ timeout: 10_000 })
    // Check palette categories using headings
    await expect(page.getByRole('heading', { name: 'Flow' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Modifiers' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Automation' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Progression' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Logic' })).toBeVisible()
  })

  test('displays the editor toolbar', async ({ page }) => {
    await page.goto('/editor')
    // Use exact: true to avoid matching "Download JSON" and "Upload JSON"
    await expect(page.getByRole('button', { name: 'Load', exact: true })).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Download JSON' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Upload JSON' })).toBeVisible()
  })

  test('can open load dropdown', async ({ page }) => {
    await page.goto('/editor')
    const loadButton = page.getByRole('button', { name: 'Load', exact: true })
    await expect(loadButton).toBeVisible({ timeout: 10_000 })
    await loadButton.click()
    // Should show a dropdown with available games (from the API)
    await expect(page.getByText(/minicap|MiniCap|No games found/i)).toBeVisible({ timeout: 10_000 })
  })
})
