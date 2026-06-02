/**
 * Unit tests for ErrorDisplay component.
 * Tests rendering in different variants and with different error categories.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ErrorDisplay } from '@/components/ui/error-display'

// Mock lucide-react icons since they're React components
vi.mock('lucide-react', () => ({
  AlertCircle: (props: any) => <svg data-testid="icon-alert" {...props} />,
  WifiOff: (props: any) => <svg data-testid="icon-wifi" {...props} />,
  Lock: (props: any) => <svg data-testid="icon-lock" {...props} />,
  ServerCrash: (props: any) => <svg data-testid="icon-server" {...props} />,
  Clock: (props: any) => <svg data-testid="icon-clock" {...props} />,
  SearchX: (props: any) => <svg data-testid="icon-search" {...props} />,
  RefreshCcw: (props: any) => <svg data-testid="icon-refresh" {...props} />,
}))

describe('ErrorDisplay', () => {
  // ─── Card variant (default) ───────────────────────────────────

  describe('card variant', () => {
    it('renders with default unknown category', () => {
      render(<ErrorDisplay />)
      expect(screen.getByText('Something Went Wrong')).toBeInTheDocument()
    })

    it('renders with explicit category', () => {
      render(<ErrorDisplay category="network" />)
      expect(screen.getByText('Network Connection Error')).toBeInTheDocument()
    })

    it('renders error message from string error', () => {
      render(<ErrorDisplay error="Custom error message" />)
      expect(screen.getByText('Custom error message')).toBeInTheDocument()
    })

    it('renders error message from Error object', () => {
      const error = new Error('Something broke')
      render(<ErrorDisplay error={error} />)
      expect(screen.getByText('Something broke')).toBeInTheDocument()
    })

    it('renders custom title and message', () => {
      render(
        <ErrorDisplay
          title="Custom Title"
          message="Custom Message"
        />
      )
      expect(screen.getByText('Custom Title')).toBeInTheDocument()
      expect(screen.getByText('Custom Message')).toBeInTheDocument()
    })

    it('renders retry button when onRetry provided', () => {
      const onRetry = vi.fn()
      render(<ErrorDisplay onRetry={onRetry} />)
      // unknown category default label is "Retry"
      expect(screen.getByText('Retry')).toBeInTheDocument()
    })

    it('calls onRetry when retry button clicked', () => {
      const onRetry = vi.fn()
      render(<ErrorDisplay onRetry={onRetry} />)
      fireEvent.click(screen.getByText('Retry'))
      expect(onRetry).toHaveBeenCalledTimes(1)
    })

    it('renders custom retry label', () => {
      const onRetry = vi.fn()
      render(<ErrorDisplay onRetry={onRetry} retryLabel="Reload" />)
      expect(screen.getByText('Reload')).toBeInTheDocument()
    })

    it('does not render retry button without onRetry', () => {
      render(<ErrorDisplay />)
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })
  })

  // ─── Simple variant ──────────────────────────────────────────

  describe('simple variant', () => {
    it('renders simple variant with message', () => {
      render(<ErrorDisplay variant="simple" error="Simple error" />)
      expect(screen.getByText('Simple error')).toBeInTheDocument()
    })

    it('renders retry link in simple variant', () => {
      const onRetry = vi.fn()
      render(<ErrorDisplay variant="simple" onRetry={onRetry} />)
      // unknown category default label is "Retry"
      expect(screen.getByText('Retry')).toBeInTheDocument()
    })

    it('calls onRetry in simple variant', () => {
      const onRetry = vi.fn()
      render(<ErrorDisplay variant="simple" onRetry={onRetry} />)
      fireEvent.click(screen.getByText('Retry'))
      expect(onRetry).toHaveBeenCalledTimes(1)
    })
  })

  // ─── Inline variant ─────────────────────────────────────────

  describe('inline variant', () => {
    it('renders inline variant with title and message', () => {
      render(<ErrorDisplay variant="inline" category="network" />)
      expect(screen.getByText('Network Connection Error')).toBeInTheDocument()
      expect(screen.getByText(/check your internet/i)).toBeInTheDocument()
    })

    it('renders retry button in inline variant', () => {
      const onRetry = vi.fn()
      render(<ErrorDisplay variant="inline" onRetry={onRetry} />)
      // unknown category default label is "Retry"
      expect(screen.getByText('Retry')).toBeInTheDocument()
    })
  })

  // ─── Language support ────────────────────────────────────────

  describe('language support', () => {
    it('renders Chinese messages when lang=zh', () => {
      render(<ErrorDisplay lang="zh" category="network" />)
      expect(screen.getByText('网络连接错误')).toBeInTheDocument()
    })

    it('renders Chinese retry label', () => {
      const onRetry = vi.fn()
      render(<ErrorDisplay lang="zh" category="network" onRetry={onRetry} />)
      expect(screen.getByText('检查连接')).toBeInTheDocument()
    })
  })

  // ─── Category-specific icons ─────────────────────────────────

  describe('category icons', () => {
    it('renders correct icon for network errors', () => {
      render(<ErrorDisplay category="network" />)
      expect(screen.getByTestId('icon-wifi')).toBeInTheDocument()
    })

    it('renders correct icon for auth errors', () => {
      render(<ErrorDisplay category="auth" />)
      expect(screen.getByTestId('icon-lock')).toBeInTheDocument()
    })

    it('renders correct icon for timeout errors', () => {
      render(<ErrorDisplay category="timeout" />)
      expect(screen.getByTestId('icon-clock')).toBeInTheDocument()
    })
  })

  // ─── Custom className ────────────────────────────────────────

  describe('custom className', () => {
    it('applies custom className to card variant', () => {
      const { container } = render(<ErrorDisplay className="my-custom-class" />)
      expect(container.firstChild).toHaveClass('my-custom-class')
    })
  })
})
