import { useState, useRef } from 'react'
import type { Node, Edge } from '@xyflow/react'

import { listGames, getGame, createGame } from '../api/games.ts'
import type { GameSummary } from '../api/types.ts'
import { graphToGame, gameToGraph } from './conversion.ts'
import type { GameDefinitionJSON } from './conversion.ts'
import type { EditorNode } from './types.ts'

interface EditorToolbarProps {
  nodes: Node[]
  edges: Edge[]
  gameName: string
  onSetGameName: (name: string) => void
  onLoadGraph: (nodes: EditorNode[], edges: Edge[]) => void
}

export default function EditorToolbar({ nodes, edges, gameName, onSetGameName, onLoadGraph }: EditorToolbarProps) {
  const [status, setStatus] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const [gameList, setGameList] = useState<GameSummary[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [loading, setLoading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function showStatus(message: string, type: 'success' | 'error') {
    setStatus({ message, type })
    setTimeout(() => setStatus(null), 3000)
  }

  async function handleLoadDropdown() {
    if (showDropdown) {
      setShowDropdown(false)
      return
    }
    try {
      setLoading(true)
      const result = await listGames()
      setGameList(result.games)
      setShowDropdown(true)
    } catch (err) {
      showStatus(`Failed to list games: ${err instanceof Error ? err.message : String(err)}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  async function handleSelectGame(gameId: string) {
    setShowDropdown(false)
    try {
      setLoading(true)
      const gameJson = await getGame(gameId) as unknown as GameDefinitionJSON
      const { nodes: newNodes, edges: newEdges } = gameToGraph(gameJson)
      onLoadGraph(newNodes, newEdges)
      onSetGameName(gameJson.name)
      showStatus(`Loaded "${gameJson.name}"`, 'success')
    } catch (err) {
      showStatus(`Failed to load game: ${err instanceof Error ? err.message : String(err)}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave() {
    if (!gameName.trim()) {
      showStatus('Please enter a game name', 'error')
      return
    }
    try {
      setLoading(true)
      const gameJson = graphToGame(
        nodes as EditorNode[],
        edges,
        { name: gameName, stacking_groups: {} },
      )
      const result = await createGame(gameJson as unknown as Record<string, unknown>)
      showStatus(`Saved "${result.name}" (id: ${result.id})`, 'success')
    } catch (err) {
      showStatus(`Failed to save: ${err instanceof Error ? err.message : String(err)}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  function handleDownload() {
    if (!gameName.trim()) {
      showStatus('Please enter a game name', 'error')
      return
    }
    try {
      const gameJson = graphToGame(
        nodes as EditorNode[],
        edges,
        { name: gameName, stacking_groups: {} },
      )
      const blob = new Blob([JSON.stringify(gameJson, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${gameName.replace(/[^a-zA-Z0-9_-]/g, '_')}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      showStatus('Downloaded JSON file', 'success')
    } catch (err) {
      showStatus(`Failed to download: ${err instanceof Error ? err.message : String(err)}`, 'error')
    }
  }

  function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string
        const gameJson = JSON.parse(text) as GameDefinitionJSON
        const { nodes: newNodes, edges: newEdges } = gameToGraph(gameJson)
        onLoadGraph(newNodes, newEdges)
        if (gameJson.name) onSetGameName(gameJson.name)
        showStatus(`Uploaded "${gameJson.name ?? file.name}"`, 'success')
      } catch (err) {
        showStatus(`Failed to parse JSON: ${err instanceof Error ? err.message : String(err)}`, 'error')
      }
    }
    reader.readAsText(file)

    // Reset file input so the same file can be re-uploaded
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const buttonClass =
    'px-3 py-1.5 text-sm font-medium rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed'

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
      {/* Game name input */}
      <label className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400">
        Game:
        <input
          type="text"
          value={gameName}
          onChange={(e) => onSetGameName(e.target.value)}
          placeholder="Untitled Game"
          className="w-44 px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 placeholder-gray-400"
        />
      </label>

      {/* Load dropdown */}
      <div className="relative">
        <button
          className={buttonClass}
          onClick={() => void handleLoadDropdown()}
          disabled={loading}
        >
          Load
        </button>
        {showDropdown && (
          <div className="absolute top-full left-0 mt-1 w-56 max-h-60 overflow-y-auto rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-lg z-50">
            {gameList.length === 0 ? (
              <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No games found</div>
            ) : (
              gameList.map((game) => (
                <button
                  key={game.id}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => void handleSelectGame(game.id)}
                >
                  <div className="font-medium">{game.name}</div>
                  <div className="text-xs text-gray-400">
                    {game.node_count} nodes, {game.edge_count} edges
                  </div>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Save button */}
      <button
        className={buttonClass}
        onClick={() => void handleSave()}
        disabled={loading}
      >
        Save
      </button>

      {/* Download JSON */}
      <button
        className={buttonClass}
        onClick={handleDownload}
      >
        Download JSON
      </button>

      {/* Upload JSON */}
      <button
        className={buttonClass}
        onClick={() => fileInputRef.current?.click()}
      >
        Upload JSON
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleUpload}
        className="hidden"
      />

      {/* Status message */}
      {status && (
        <span
          className={`ml-auto text-sm font-medium ${
            status.type === 'success'
              ? 'text-green-600 dark:text-green-400'
              : 'text-red-600 dark:text-red-400'
          }`}
        >
          {status.message}
        </span>
      )}
    </div>
  )
}
