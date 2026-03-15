import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ErrorBanner from '../ErrorBanner'

describe('ErrorBanner', () => {
  it('renders error message', () => {
    render(<ErrorBanner message="Something went wrong" />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('does not render dismiss button when onDismiss is not provided', () => {
    render(<ErrorBanner message="Error" />)
    expect(screen.queryByRole('button', { name: /dismiss/i })).not.toBeInTheDocument()
  })

  it('renders dismiss button and calls onDismiss when clicked', async () => {
    const onDismiss = vi.fn()
    render(<ErrorBanner message="Error" onDismiss={onDismiss} />)
    const button = screen.getByRole('button', { name: /dismiss/i })
    expect(button).toBeInTheDocument()
    await userEvent.click(button)
    expect(onDismiss).toHaveBeenCalledOnce()
  })
})
