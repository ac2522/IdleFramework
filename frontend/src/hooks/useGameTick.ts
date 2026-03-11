import { useEffect, useRef, useState, useCallback } from 'react'

interface UseGameTickOptions {
  onTick: (seconds: number) => Promise<void>
  tickIntervalMs?: number
  onError?: (err: unknown) => void
}

interface UseGameTickReturn {
  running: boolean
  speed: number
  setSpeed: (s: number) => void
  pause: () => void
  resume: () => void
  toggle: () => void
}

export function useGameTick({ onTick, tickIntervalMs = 1000, onError }: UseGameTickOptions): UseGameTickReturn {
  const [running, setRunning] = useState(false)
  const [speed, setSpeed] = useState(1)
  const onTickRef = useRef(onTick)
  const speedRef = useRef(speed)
  const onErrorRef = useRef(onError)
  const tickingRef = useRef(false)

  useEffect(() => {
    onTickRef.current = onTick
    speedRef.current = speed
    onErrorRef.current = onError
  })

  const pause = useCallback(() => setRunning(false), [])
  const resume = useCallback(() => setRunning(true), [])
  const toggle = useCallback(() => setRunning(r => !r), [])

  useEffect(() => {
    if (!running) return

    const id = setInterval(() => {
      if (tickingRef.current) return
      tickingRef.current = true
      onTickRef.current(speedRef.current).catch((err) => {
        if (onErrorRef.current) onErrorRef.current(err)
      }).finally(() => {
        tickingRef.current = false
      })
    }, tickIntervalMs)

    return () => clearInterval(id)
  }, [running, tickIntervalMs])

  return { running, speed, setSpeed, pause, resume, toggle }
}
