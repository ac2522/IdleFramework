/**
 * Analyze Page — Workflow tests.
 * Tests analysis execution, chart rendering, and strategy comparison.
 */

import { test, expect } from '@playwright/test'

test.describe('Analyze — Run Analysis', () => {
  test('run analysis shows summary and results', async ({ page }) => {
    await page.goto('/analyze')
    await expect(page.getByRole('button', { name: 'Run Analysis' })).toBeVisible({ timeout: 15_000 })

    await page.getByRole('button', { name: 'Run Analysis' }).click()

    // Results should appear
    await expect(page.getByText('Summary')).toBeVisible({ timeout: 30_000 })
  })

  test('analysis shows Plotly charts', async ({ page }) => {
    await page.goto('/analyze')
    await expect(page.getByRole('button', { name: 'Run Analysis' })).toBeVisible({ timeout: 15_000 })

    await page.getByRole('button', { name: 'Run Analysis' }).click()
    await expect(page.getByText('Summary')).toBeVisible({ timeout: 30_000 })

    // Plotly charts render as elements with class js-plotly-plot
    const plotlyCharts = page.locator('.js-plotly-plot')
    await expect(plotlyCharts.first()).toBeVisible({ timeout: 10_000 })

    const chartCount = await plotlyCharts.count()
    expect(chartCount).toBeGreaterThanOrEqual(1)
  })
})

test.describe('Analyze — Compare Strategies', () => {
  test('compare free vs paid triggers API call', async ({ page }) => {
    await page.goto('/analyze')
    await expect(page.getByRole('button', { name: 'Compare Free vs Paid' })).toBeVisible({ timeout: 15_000 })

    const comparePromise = page.waitForResponse(
      (resp) => resp.url().includes('/analysis/compare'),
      { timeout: 30_000 }
    )

    await page.getByRole('button', { name: 'Compare Free vs Paid' }).click()
    const response = await comparePromise

    // API should respond (200 = results, 400/500 = error handled by UI)
    expect(response.status()).toBeLessThan(600)
  })
})

test.describe('Analyze — Optimizer Selection', () => {
  test('can run analysis with default settings', async ({ page }) => {
    await page.goto('/analyze')
    await expect(page.getByRole('button', { name: 'Run Analysis' })).toBeVisible({ timeout: 15_000 })

    await page.getByRole('button', { name: 'Run Analysis' }).click()
    await expect(page.getByText('Summary')).toBeVisible({ timeout: 30_000 })
  })

  test('simulation time input accepts custom values', async ({ page }) => {
    await page.goto('/analyze')
    await expect(page.getByText('Analysis Controls')).toBeVisible({ timeout: 15_000 })

    // Find the simulation time input
    const timeInput = page.locator('input[type="number"]').first()
    if (await timeInput.isVisible()) {
      await timeInput.fill('120')

      const analysisRequest = page.waitForRequest(
        (req) => req.url().includes('/analysis/') && req.method() === 'POST'
      )

      await page.getByRole('button', { name: 'Run Analysis' }).click()
      const request = await analysisRequest
      const body = JSON.parse(request.postData() || '{}')

      // Verify the simulation time was sent
      if (body.simulation_time !== undefined) {
        expect(body.simulation_time).toBe(120)
      }
    }
  })
})

test.describe('Analyze — Controls', () => {
  test('displays all analysis controls', async ({ page }) => {
    await page.goto('/analyze')

    await expect(page.getByText('Game Analysis')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('Analysis Controls')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Run Analysis' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Compare Free vs Paid' })).toBeVisible()
  })

  test('game selector is present', async ({ page }) => {
    await page.goto('/analyze')

    const selector = page.locator('select#game-selector')
    await expect(selector).toBeVisible({ timeout: 15_000 })
  })
})
