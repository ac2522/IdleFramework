import { describe, it, expect } from 'vitest'
import { formatNumber, formatTime } from '../formatting'

describe('formatNumber', () => {
  it('handles zero', () => {
    expect(formatNumber(0)).toBe('0')
  })

  it('formats small numbers with one decimal when < 10', () => {
    expect(formatNumber(3.14)).toBe('3.1')
  })

  it('formats numbers >= 10 and < 1000 with no decimals', () => {
    expect(formatNumber(42)).toBe('42')
    expect(formatNumber(999)).toBe('999')
  })

  it('formats very small numbers in exponential notation', () => {
    expect(formatNumber(0.001)).toBe('1.00e-3')
  })

  it('formats thousands with K suffix', () => {
    expect(formatNumber(1500)).toBe('1.50 K')
  })

  it('formats millions with M suffix', () => {
    expect(formatNumber(2_500_000)).toBe('2.50 M')
  })

  it('formats billions with B suffix', () => {
    expect(formatNumber(1_000_000_000)).toBe('1.00 B')
  })
})

describe('formatTime', () => {
  it('formats seconds with one decimal', () => {
    expect(formatTime(45)).toBe('45.0s')
  })

  it('formats minutes and remaining seconds', () => {
    expect(formatTime(120)).toBe('2m 0s')
    expect(formatTime(90)).toBe('1m 30s')
  })

  it('formats hours and remaining minutes', () => {
    expect(formatTime(7200)).toBe('2h 0m')
    expect(formatTime(3661)).toBe('1h 1m')
  })
})
