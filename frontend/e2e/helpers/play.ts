/**
 * Play page helpers for Playwright E2E tests.
 */

import type { Page } from '@playwright/test'

/** Wait for the play page to fully load with a session. */
export async function waitForPlayPage(page: Page) {
  await page.waitForSelector('text=Resources', { timeout: 15_000 })
}

/** Upload a fixture JSON and wait for the session to start. */
export async function uploadAndStartGame(page: Page, fixturePath: string) {
  await page.goto('/play')

  // Upload the fixture file via the hidden file input
  const fileInput = page.locator('#game-upload-input')
  await fileInput.setInputFiles(fixturePath)

  // Wait for the upload to create the game and start a session
  await waitForPlayPage(page)
}

/** Click the Resume button to start the game tick loop. */
export async function resumeGame(page: Page) {
  await page.getByRole('button', { name: 'Resume' }).click()
}

/** Click the Pause button to stop the game tick loop. */
export async function pauseGame(page: Page) {
  await page.getByRole('button', { name: 'Pause' }).click()
}

/** Wait for at least one advance API call to complete. */
export async function waitForTick(page: Page) {
  await page.waitForResponse(
    (resp) => resp.url().includes('/advance') && resp.status() === 200,
    { timeout: 10_000 }
  )
}

/** Click "Buy 1" on a generator card identified by name. */
export async function buyGenerator(page: Page, genName: string) {
  const card = page.locator('h4').filter({ hasText: genName }).locator('..')
  const container = card.locator('..')
  await container.getByRole('button', { name: 'Buy 1' }).click()
}
