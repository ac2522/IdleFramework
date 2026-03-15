import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Spinner from '../Spinner'

describe('Spinner', () => {
  it('renders with label', () => {
    render(<Spinner label="Loading..." />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('renders without label', () => {
    const { container } = render(<Spinner />)
    expect(container.firstChild).toBeTruthy()
  })

  it('uses default aria-label when no label provided', () => {
    render(<Spinner />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading')
  })

  it('sets aria-label from label prop', () => {
    render(<Spinner label="Please wait" />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Please wait')
  })
})
