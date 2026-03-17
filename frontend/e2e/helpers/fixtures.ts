/**
 * Fixture file resolution helpers for Playwright E2E tests.
 * Uses import.meta.url for ESM compatibility (no __dirname).
 */

import { dirname, resolve } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

/** Absolute path to the backend test fixtures directory. */
export const FIXTURE_DIR = resolve(__dirname, '..', '..', '..', 'tests', 'fixtures')

/** Absolute path to the e2e-specific fixtures. */
export const E2E_FIXTURE_DIR = resolve(FIXTURE_DIR, 'e2e')

/** Returns the absolute path to a fixture JSON file. */
export function fixturePath(name: string): string {
  // Try e2e fixtures first, fall back to main fixtures
  const e2ePath = resolve(E2E_FIXTURE_DIR, `${name}.json`)
  const mainPath = resolve(FIXTURE_DIR, `${name}.json`)

  // Return e2e path if name looks like an e2e fixture
  const e2eNames = ['cookie_clicker', 'factory_idle', 'prestige_tower', 'speed_runner', 'full_kitchen']
  if (e2eNames.includes(name)) {
    return e2ePath
  }
  return mainPath
}

/** All available fixture names (main + e2e). */
export const MAIN_FIXTURES = ['minicap', 'mediumcap'] as const
export const E2E_FIXTURES = ['cookie_clicker', 'factory_idle', 'prestige_tower', 'speed_runner', 'full_kitchen'] as const
