import { useState, useEffect, useRef, useCallback } from 'react'
import { listGames, createGame } from '../../api/games'
import type { GameSummary } from '../../api/types'

interface GameSelectorProps {
  value: string
  onChange: (gameId: string) => void
  disabled?: boolean
}

export default function GameSelector({ value, onChange, disabled = false }: GameSelectorProps) {
  const [games, setGames] = useState<GameSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchGames = useCallback(async () => {
    try {
      setLoading(true)
      const { games: g } = await listGames()
      setGames(g)
      // If current value is not in the list, select the first game
      if (g.length > 0 && !g.find((x) => x.id === value)) {
        onChange(g[0].id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load games')
    } finally {
      setLoading(false)
    }
  }, [value, onChange])

  useEffect(() => {
    fetchGames()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleFileUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return

      setUploading(true)
      setError(null)

      try {
        const text = await file.text()
        const json = JSON.parse(text)
        const result = await createGame(json)
        // Refresh game list and select the new game
        await fetchGames()
        onChange(result.id)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to upload game')
      } finally {
        setUploading(false)
        // Reset the file input so the same file can be uploaded again
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      }
    },
    [fetchGames, onChange],
  )

  return (
    <div className="flex items-end gap-3">
      <div className="flex-1">
        <label htmlFor="game-selector" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
          Game
        </label>
        <select
          id="game-selector"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled || loading}
          className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        >
          {loading && <option>Loading...</option>}
          {!loading && games.length === 0 && <option value={value}>{value}</option>}
          {games.map((g) => (
            <option key={g.id} value={g.id}>
              {g.name} ({g.node_count} nodes)
            </option>
          ))}
        </select>
      </div>

      <div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={handleFileUpload}
          className="hidden"
          id="game-upload-input"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || uploading}
          className={`rounded-md border px-3 py-2 text-sm font-medium shadow-sm transition-colors cursor-pointer ${
            uploading
              ? 'border-gray-300 bg-gray-100 text-gray-400 cursor-not-allowed dark:border-gray-600 dark:bg-gray-700 dark:text-gray-500'
              : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          {uploading ? 'Uploading...' : 'Upload JSON'}
        </button>
      </div>

      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}
