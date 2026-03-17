/**
 * Play Page — Gameplay interaction tests.
 * Tests actual gameplay flows: purchases, production, speed, prestige, auto-optimize.
 */

import { test, expect } from '@playwright/test'
import { fixturePath } from './helpers/fixtures'
import { waitForPlayPage, resumeGame, pauseGame, uploadAndStartGame } from './helpers/play'

test.describe('Play — Production Tick', () => {
  test('production tick fires after resume and returns updated state', async ({ page }) => {
    await page.goto('/play')
    await waitForPlayPage(page)

    // Set up response listener BEFORE resuming
    const advancePromise = page.waitForResponse(
      (resp) => resp.url().includes('/advance') && resp.status() === 200,
      { timeout: 10_000 }
    )

    await resumeGame(page)
    const response = await advancePromise
    const body = await response.json()

    expect(body.session_id).toBeTruthy()
    expect(body.elapsed_time).toBeGreaterThan(0)

    await pauseGame(page)
  })

  test('pause stops advance API calls', async ({ page }) => {
    await page.goto('/play')
    await waitForPlayPage(page)

    // Start ticking
    await resumeGame(page)
    await page.waitForResponse((r) => r.url().includes('/advance'), { timeout: 10_000 })
    await pauseGame(page)

    // After pausing, no more advance calls should fire
    let advanceFired = false
    page.on('response', (resp) => {
      if (resp.url().includes('/advance')) advanceFired = true
    })

    // Wait a bit — no advance should fire
    await page.waitForTimeout(2000)
    expect(advanceFired).toBe(false)
  })
})

test.describe('Play — Generator Purchase', () => {
  test('Buy 1 triggers purchase API and returns updated state', async ({ page }) => {
    await page.goto('/play')
    await waitForPlayPage(page)

    const buyButton = page.getByRole('button', { name: 'Buy 1' }).first()
    await expect(buyButton).toBeVisible({ timeout: 10_000 })

    const purchasePromise = page.waitForResponse(
      (resp) => resp.url().includes('/purchase') && resp.status() === 200,
      { timeout: 10_000 }
    )

    await buyButton.click()
    const response = await purchasePromise
    const body = await response.json()

    expect(body.session_id).toBeTruthy()
  })

  test('Buy 10 triggers purchase with count=10', async ({ page }) => {
    await page.goto('/play')
    await waitForPlayPage(page)

    const buy10Button = page.getByRole('button', { name: 'Buy 10' }).first()
    await expect(buy10Button).toBeVisible({ timeout: 10_000 })

    const purchasePromise = page.waitForRequest(
      (req) => req.url().includes('/purchase') && req.method() === 'POST'
    )

    await buy10Button.click()
    const request = await purchasePromise
    const body = JSON.parse(request.postData() || '{}')

    expect(body.count).toBe(10)
  })
})

test.describe('Play — Speed Controls', () => {
  test('changing speed affects advance seconds', async ({ page }) => {
    await page.goto('/play')
    await waitForPlayPage(page)

    // Click 10x speed
    await page.getByRole('button', { name: '10x' }).click()

    // Set up request listener, then resume
    const advancePromise = page.waitForRequest(
      (req) => req.url().includes('/advance') && req.method() === 'POST'
    )

    await resumeGame(page)
    const request = await advancePromise
    const body = JSON.parse(request.postData() || '{}')

    expect(body.seconds).toBe(10)

    await pauseGame(page)
  })

  test('100x speed sends seconds=100', async ({ page }) => {
    await page.goto('/play')
    await waitForPlayPage(page)

    await page.getByRole('button', { name: '100x' }).click()

    const advancePromise = page.waitForRequest(
      (req) => req.url().includes('/advance') && req.method() === 'POST'
    )

    await resumeGame(page)
    const request = await advancePromise
    const body = JSON.parse(request.postData() || '{}')

    expect(body.seconds).toBe(100)

    await pauseGame(page)
  })
})

test.describe('Play — Auto-Optimize', () => {
  test('auto-optimize shows timeline then clear hides it', async ({ page }) => {
    await page.goto('/play')
    await waitForPlayPage(page)

    const optimizeButton = page.getByRole('button', { name: 'Auto-Optimize' })
    await expect(optimizeButton).toBeVisible()

    const optimizePromise = page.waitForResponse(
      (resp) => resp.url().includes('/auto-optimize') && resp.status() === 200,
      { timeout: 30_000 }
    )

    await optimizeButton.click()
    await optimizePromise

    // Timeline should appear with stats
    await expect(page.getByText('Optimizer Timeline')).toBeVisible({ timeout: 5_000 })
    await expect(page.getByText('Final Production')).toBeVisible()
    await expect(page.getByText('Purchases')).toBeVisible()

    // Clear should hide it
    await page.getByRole('button', { name: 'Clear' }).click()
    await expect(page.getByText('Optimizer Timeline')).not.toBeVisible()
  })
})

test.describe('Play — Game Selector', () => {
  test('game selector has options', async ({ page }) => {
    await page.goto('/play')
    await waitForPlayPage(page)

    const selector = page.locator('select#game-selector')
    await expect(selector).toBeVisible()

    const optionCount = await selector.locator('option').count()
    expect(optionCount).toBeGreaterThan(0)
  })
})

test.describe('Play — Prestige', () => {
  test('prestige panel is visible with prestige button', async ({ page }) => {
    await page.goto('/play')
    await waitForPlayPage(page)

    // For MiniCap, prestige panel exists
    await expect(page.getByRole('heading', { name: 'Prestige' })).toBeVisible({ timeout: 10_000 })
    // The button exists (may be disabled if no currency available)
    await expect(page.getByRole('button', { name: 'Prestige Now' })).toBeVisible()
  })
})

test.describe('Play — Fixture Upload', () => {
  test('upload CookieClicker fixture starts a valid session', async ({ page }) => {
    await uploadAndStartGame(page, fixturePath('cookie_clicker'))

    await expect(page.getByText('Resources')).toBeVisible()
    await expect(page.getByText('Generators')).toBeVisible()
  })
})
