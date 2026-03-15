import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ResourceDisplay from '../ResourceDisplay'

describe('ResourceDisplay', () => {
  it('renders resource names and formatted values', () => {
    const resources = {
      gold: { current_value: 100, production_rate: 5 },
    }
    render(<ResourceDisplay resources={resources} />)
    expect(screen.getByText('gold')).toBeInTheDocument()
    // formatNumber(100) => "100"
    expect(screen.getByText('100')).toBeInTheDocument()
  })

  it('shows production rate when positive', () => {
    const resources = {
      gold: { current_value: 50, production_rate: 2.5 },
    }
    render(<ResourceDisplay resources={resources} />)
    // formatNumber(2.5) => "2.5", displayed as "+2.5/s"
    expect(screen.getByText('+2.5/s')).toBeInTheDocument()
  })

  it('hides production rate when zero', () => {
    const resources = {
      gold: { current_value: 50, production_rate: 0 },
    }
    render(<ResourceDisplay resources={resources} />)
    expect(screen.queryByText(/\/s/)).not.toBeInTheDocument()
  })

  it('renders empty state when no resources', () => {
    render(<ResourceDisplay resources={{}} />)
    expect(screen.getByText('No resources')).toBeInTheDocument()
  })

  it('renders multiple resources', () => {
    const resources = {
      gold: { current_value: 100, production_rate: 0 },
      gems: { current_value: 5, production_rate: 1 },
    }
    render(<ResourceDisplay resources={resources} />)
    expect(screen.getByText('gold')).toBeInTheDocument()
    expect(screen.getByText('gems')).toBeInTheDocument()
  })
})
