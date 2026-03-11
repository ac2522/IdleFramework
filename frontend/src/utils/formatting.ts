const SUFFIXES = ['', 'K', 'M', 'B', 'T', 'Qa', 'Qi', 'Sx', 'Sp', 'Oc', 'No', 'Dc']

export function formatNumber(value: number): string {
  if (value === 0) return '0'
  if (Math.abs(value) < 0.01) return value.toExponential(2)
  if (Math.abs(value) < 1000) return value.toFixed(value < 10 ? 1 : 0)

  const tier = Math.floor(Math.log10(Math.abs(value)) / 3)
  if (tier > 0 && tier < SUFFIXES.length) {
    const scaled = value / Math.pow(10, tier * 3)
    return `${scaled.toFixed(2)} ${SUFFIXES[tier]}`
  }
  const exp = Math.floor(Math.log10(Math.abs(value)))
  const mant = value / Math.pow(10, exp)
  return `${mant.toFixed(2)}e${exp}`
}

export function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}
