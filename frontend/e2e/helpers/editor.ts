/**
 * Editor page helpers for Playwright E2E tests.
 */

import type { Page } from '@playwright/test'

/** Wait for the editor page canvas to be ready. */
export async function waitForEditorPage(page: Page) {
  await page.waitForSelector('.react-flow', { timeout: 15_000 })
}

/** Upload a fixture JSON file into the editor via the toolbar Upload JSON button. */
export async function uploadFixtureInEditor(page: Page, fixturePath: string) {
  await page.goto('/editor')
  await waitForEditorPage(page)

  // The hidden file input for Upload JSON in the editor toolbar
  const fileInput = page.locator('input[type="file"][accept=".json"]')
  await fileInput.setInputFiles(fixturePath)

  // Wait for nodes to appear on the canvas
  await page.waitForSelector('.react-flow__node', { timeout: 10_000 })
}

/** Get the count of nodes on the React Flow canvas. */
export async function getNodeCount(page: Page): Promise<number> {
  return page.locator('.react-flow__node').count()
}

/** Get the count of edges on the React Flow canvas. */
export async function getEdgeCount(page: Page): Promise<number> {
  return page.locator('.react-flow__edge').count()
}

/** Click on a React Flow node by its visible text/label. */
export async function selectNode(page: Page, label: string) {
  await page.locator('.react-flow__node').filter({ hasText: label }).click()
}

/**
 * Drag a node from the palette onto the canvas using synthetic HTML5 drag events.
 * Playwright's built-in dragTo doesn't set dataTransfer, which React Flow requires.
 */
export async function dragNodeFromPalette(
  page: Page,
  nodeTypeName: string,
  targetX = 400,
  targetY = 300
) {
  // Find the palette item
  const paletteItem = page.locator('[draggable="true"]').filter({ hasText: nodeTypeName }).first()
  await paletteItem.waitFor({ state: 'visible' })

  // Get the node type from the palette item's data attribute or text
  const nodeType = nodeTypeName.toLowerCase().replace(/ /g, '_')

  // Get canvas position
  const canvas = page.locator('.react-flow')
  const canvasBox = await canvas.boundingBox()
  if (!canvasBox) throw new Error('Canvas not visible')

  const dropX = canvasBox.x + targetX
  const dropY = canvasBox.y + targetY

  // Dispatch synthetic HTML5 drag events with DataTransfer
  await page.evaluate(
    ({ type, x, y }) => {
      const reactFlowPane = document.querySelector('.react-flow__pane')
      if (!reactFlowPane) throw new Error('React Flow pane not found')

      const dt = new DataTransfer()
      dt.setData('application/reactflow', type)

      const dragOverEvent = new DragEvent('dragover', {
        bubbles: true,
        cancelable: true,
        clientX: x,
        clientY: y,
        dataTransfer: dt,
      })
      reactFlowPane.dispatchEvent(dragOverEvent)

      const dropEvent = new DragEvent('drop', {
        bubbles: true,
        cancelable: true,
        clientX: x,
        clientY: y,
        dataTransfer: dt,
      })
      reactFlowPane.dispatchEvent(dropEvent)
    },
    { type: nodeType, x: dropX, y: dropY }
  )
}
