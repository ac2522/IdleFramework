import { useState, useMemo } from 'react'
import type { Edge } from '@xyflow/react'

import type { EditorNode } from './types.ts'
import { graphToGame } from './conversion.ts'

interface JsonPreviewProps {
  nodes: EditorNode[]
  edges: Edge[]
  gameName: string
}

export default function JsonPreview({ nodes, edges, gameName }: JsonPreviewProps) {
  const [open, setOpen] = useState(false)

  const jsonText = useMemo(() => {
    if (!open) return ''
    const game = graphToGame(nodes, edges, {
      name: gameName,
      stacking_groups: {},
    })
    return JSON.stringify(game, null, 2)
  }, [open, nodes, edges, gameName])

  return (
    <div className="border-t border-gray-200 dark:border-gray-700">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full px-3 py-2 text-left text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none"
      >
        {open ? '▾' : '▸'} JSON Preview
      </button>

      {open && (
        <pre className="m-2 max-h-96 overflow-auto rounded bg-gray-100 dark:bg-gray-900 p-3 text-xs text-gray-800 dark:text-green-400 font-mono">
          {jsonText}
        </pre>
      )}
    </div>
  )
}
