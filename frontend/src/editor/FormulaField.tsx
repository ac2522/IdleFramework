import { useState, useEffect, useRef } from 'react'

interface FormulaFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
}

function validateFormula(formula: string): { valid: boolean; message: string } {
  if (formula.trim() === '') {
    return { valid: false, message: 'Formula cannot be empty' }
  }

  let depth = 0
  for (const ch of formula) {
    if (ch === '(') depth++
    else if (ch === ')') depth--
    if (depth < 0) {
      return { valid: false, message: 'Unmatched closing parenthesis' }
    }
  }
  if (depth > 0) {
    return { valid: false, message: 'Unmatched opening parenthesis' }
  }

  return { valid: true, message: 'Valid syntax' }
}

export default function FormulaField({ label, value, onChange }: FormulaFieldProps) {
  const [localValue, setLocalValue] = useState(value)
  const [validation, setValidation] = useState<{ valid: boolean; message: string } | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sync from parent when value prop changes
  useEffect(() => {
    setLocalValue(value)
  }, [value])

  function handleChange(newValue: string) {
    setLocalValue(newValue)

    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }

    timerRef.current = setTimeout(() => {
      const result = validateFormula(newValue)
      setValidation(result)
      onChange(newValue)
    }, 300)
  }

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [])

  return (
    <div className="mb-3">
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
        {label}
      </label>
      <textarea
        value={localValue}
        onChange={(e) => handleChange(e.target.value)}
        rows={3}
        className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      {validation && (
        <p className={`mt-0.5 text-xs ${validation.valid ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
          {validation.message}
        </p>
      )}
    </div>
  )
}
