import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import GeneratorCard from '../GeneratorCard'

describe('GeneratorCard', () => {
  const defaultProps = {
    name: 'Miner',
    gen: { owned: 5, cost_next: 100, production_per_sec: 2.5 },
    balance: 200,
    onBuy: vi.fn(),
  }

  it('renders generator name and owned count', () => {
    render(<GeneratorCard {...defaultProps} />)
    expect(screen.getByText('Miner')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('renders production rate', () => {
    render(<GeneratorCard {...defaultProps} />)
    // formatNumber(2.5) => "2.5", displayed as "2.5/s"
    expect(screen.getByText('2.5/s')).toBeInTheDocument()
  })

  it('calls onBuy with 1 when Buy 1 button is clicked', async () => {
    const onBuy = vi.fn()
    render(<GeneratorCard {...defaultProps} onBuy={onBuy} />)
    await userEvent.click(screen.getByText('Buy 1'))
    expect(onBuy).toHaveBeenCalledWith(1)
  })

  it('calls onBuy with 10 when Buy 10 button is clicked', async () => {
    const onBuy = vi.fn()
    render(<GeneratorCard {...defaultProps} onBuy={onBuy} />)
    await userEvent.click(screen.getByText('Buy 10'))
    expect(onBuy).toHaveBeenCalledWith(10)
  })

  it('disables buy buttons when balance is insufficient', () => {
    render(<GeneratorCard {...defaultProps} balance={50} />)
    expect(screen.getByText('Buy 1')).toBeDisabled()
    expect(screen.getByText('Buy 10')).toBeDisabled()
  })

  it('enables buy buttons when balance is sufficient', () => {
    render(<GeneratorCard {...defaultProps} balance={200} />)
    expect(screen.getByText('Buy 1')).toBeEnabled()
    expect(screen.getByText('Buy 10')).toBeEnabled()
  })
})
