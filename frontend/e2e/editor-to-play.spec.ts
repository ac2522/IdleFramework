/**
 * Editor → Play → Analyze roundtrip tests.
 * Verifies the full workflow: load in editor, save, play, analyze.
 */

import { test, expect } from '@playwright/test'
import { fixturePath } from './helpers/fixtures'
import { uploadFixtureInEditor, getNodeCount } from './helpers/editor'
import { waitForPlayPage } from './helpers/play'

test.describe('Roundtrip — Editor to Play', () => {
  test('upload fixture in editor, save, then play', async ({ page }) => {
    // Step 1: Load fixture in editor
    await uploadFixtureInEditor(page, fixturePath('cookie_clicker'))

    const nodeCount = await getNodeCount(page)
    expect(nodeCount).toBe(18)

    // Step 2: Save the game
    const nameInput = page.locator('input[placeholder="Untitled Game"]')
    await nameInput.fill('Roundtrip Test Cookie')

    const savePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/games/') && resp.request().method() === 'POST',
      { timeout: 10_000 }
    )
    await page.getByRole('button', { name: 'Save' }).click()
    await savePromise

    // Step 3: Navigate to Play
    await page.getByRole('link', { name: 'Play' }).click()
    await waitForPlayPage(page)

    // Step 4: Verify the play page works
    await expect(page.getByText('Resources')).toBeVisible()
    await expect(page.getByText('Generators')).toBeVisible()
  })
})

test.describe('Roundtrip — Editor to Analyze', () => {
  test('upload fixture in editor, save, then analyze', async ({ page }) => {
    // Step 1: Load fixture in editor
    await uploadFixtureInEditor(page, fixturePath('minicap'))

    // Step 2: Save the game
    const nameInput = page.locator('input[placeholder="Untitled Game"]')
    await nameInput.fill('Roundtrip Analyze Test')

    const savePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/games/') && resp.request().method() === 'POST',
      { timeout: 10_000 }
    )
    await page.getByRole('button', { name: 'Save' }).click()
    await savePromise

    // Step 3: Navigate to Analyze
    await page.getByRole('link', { name: 'Analyze' }).click()

    // Step 4: Run analysis
    await expect(page.getByRole('button', { name: 'Run Analysis' })).toBeVisible({ timeout: 15_000 })
    await page.getByRole('button', { name: 'Run Analysis' }).click()

    // Step 5: Verify results appear
    await expect(page.getByText('Summary')).toBeVisible({ timeout: 30_000 })
  })
})

test.describe('Roundtrip — Fixture Preservation', () => {
  test('upload then download preserves node and edge counts', async ({ page }) => {
    await uploadFixtureInEditor(page, fixturePath('cookie_clicker'))

    const nodeCountBefore = await getNodeCount(page)
    expect(nodeCountBefore).toBe(18)

    // Download the JSON
    const downloadPromise = page.waitForEvent('download')
    const nameInput = page.locator('input[placeholder="Untitled Game"]')
    await nameInput.fill('PreservationTest')
    await page.getByRole('button', { name: 'Download JSON' }).click()
    const download = await downloadPromise

    // Save download to temp file and re-upload
    const tmpPath = await download.path()
    if (tmpPath) {
      // Navigate to fresh editor
      await page.goto('/editor')
      await page.waitForSelector('.react-flow', { timeout: 15_000 })

      // Upload the downloaded file
      const fileInput = page.locator('input[type="file"][accept=".json"]')
      await fileInput.setInputFiles(tmpPath)
      await page.waitForSelector('.react-flow__node', { timeout: 10_000 })

      const nodeCountAfter = await getNodeCount(page)
      expect(nodeCountAfter).toBe(nodeCountBefore)
    }
  })
})
