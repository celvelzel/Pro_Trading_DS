/**
 * Integration tests for ErrorDisplay + error-messages.
 * Tests the full error display pipeline from error → categorization → display.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ErrorDisplay } from '@/components/ui/error-display'
import { categorizeError } from '@/lib/error-messages'

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  AlertCircle: (props: any) => <svg data-testid="icon-alert" {...props} />,
  WifiOff: (props: any) => <svg data-testid="icon-wifi" {...props} />,
  Lock: (props: any) => <svg data-testid="icon-lock" {...props} />,
  ServerCrash: (props: any) => <svg data-testid="icon-server" {...props} />,
  Clock: (props: any) => <svg data-testid="icon-clock" {...props} />,
  SearchX: (props: any) => <svg data-testid="icon-search" {...props} />,
  RefreshCcw: (props: any) => <svg data-testid="icon-refresh" {...props} />,
}))

describe('ErrorDisplay + error-messages integration', () => {
  // ─── Auto-categorization pipeline ────────────────────────────

  describe('auto-categorization', () => {
    it('auto-categorizes network errors and shows correct UI', () => {
      const error = { message: 'Failed to fetch' }
      const { container } = render(<ErrorDisplay error={error} />)

      // Should auto-categorize as network
      expect(categorizeError(error)).toBe('network')
      expect(screen.getByText('Network Connection Error')).toBeInTheDocument()
      // When error has a message, it's used as the display message
      expect(container.textContent).toContain('Failed to fetch')
      expect(screen.getByTestId('icon-wifi')).toBeInTheDocument()
    })

    it('auto-categorizes auth errors and shows correct UI', () => {
      const error = { code: 401 }
      render(<ErrorDisplay error={error} />)

      expect(categorizeError(error)).toBe('auth')
      expect(screen.getByText('Authentication Required')).toBeInTheDocument()
      expect(screen.getByTestId('icon-lock')).toBeInTheDocument()
    })

    it('auto-categorizes timeout errors and shows correct UI', () => {
      const error = { message: 'Request timeout' }
      render(<ErrorDisplay error={error} />)

      expect(categorizeError(error)).toBe('timeout')
      expect(screen.getByText('Request Timeout')).toBeInTheDocument()
      expect(screen.getByTestId('icon-clock')).toBeInTheDocument()
    })

    it('auto-categorizes market errors and shows correct UI', () => {
      const error = { message: 'Market data unavailable for this ticker' }
      render(<ErrorDisplay error={error} />)

      expect(categorizeError(error)).toBe('market')
      expect(screen.getByText('Market Data Unavailable')).toBeInTheDocument()
    })

    it('auto-categorizes validation errors and shows correct UI', () => {
      const error = { code: 422, message: 'Validation failed' }
      render(<ErrorDisplay error={error} />)

      expect(categorizeError(error)).toBe('validation')
      expect(screen.getByText('Invalid Data')).toBeInTheDocument()
    })

    it('auto-categorizes API/server errors and shows correct UI', () => {
      const error = { code: 500 }
      render(<ErrorDisplay error={error} />)

      expect(categorizeError(error)).toBe('api')
      expect(screen.getByText('Server Error')).toBeInTheDocument()
      expect(screen.getByTestId('icon-server')).toBeInTheDocument()
    })
  })

  // ─── Override auto-categorization ────────────────────────────

  describe('explicit category override', () => {
    it('uses explicit category over auto-detection', () => {
      // Error looks like network, but we force auth
      const error = { message: 'Network request failed' }
      render(<ErrorDisplay error={error} category="auth" />)

      expect(screen.getByText('Authentication Required')).toBeInTheDocument()
      expect(screen.getByTestId('icon-lock')).toBeInTheDocument()
    })
  })

  // ─── Chinese localization with auto-categorization ───────────

  describe('Chinese localization with auto-categorization', () => {
    it('shows Chinese messages for auto-categorized network error', () => {
      const error = { message: 'fetch failed' }
      const { container } = render(<ErrorDisplay error={error} lang="zh" />)

      expect(screen.getByText('网络连接错误')).toBeInTheDocument()
      // When error has a message, it's used as the display message
      expect(container.textContent).toContain('fetch failed')
    })

    it('shows Chinese retry button for auto-categorized timeout error', () => {
      const error = { code: 504 }
      const onRetry = vi.fn()
      render(<ErrorDisplay error={error} lang="zh" onRetry={onRetry} />)

      expect(screen.getByText('重试')).toBeInTheDocument()
    })
  })

  // ─── Error message fallback chain ────────────────────────────

  describe('error message fallback chain', () => {
    it('uses error.message when no custom message provided', () => {
      const error = new Error('Specific error details')
      render(<ErrorDisplay error={error} />)

      expect(screen.getByText('Specific error details')).toBeInTheDocument()
    })

    it('uses string error as message', () => {
      render(<ErrorDisplay error="String error message" />)
      expect(screen.getByText('String error message')).toBeInTheDocument()
    })

    it('falls back to category default message when error has no message', () => {
      render(<ErrorDisplay error={{}} />)
      // unknown category default
      expect(screen.getByText(/unexpected error/)).toBeInTheDocument()
    })

    it('custom message overrides everything', () => {
      render(
        <ErrorDisplay
          error={new Error('Original')}
          message="Override message"
        />
      )
      expect(screen.getByText('Override message')).toBeInTheDocument()
      expect(screen.queryByText('Original')).not.toBeInTheDocument()
    })
  })

  // ─── Retry flow integration ──────────────────────────────────

  describe('retry flow', () => {
    it('retry works across all variants', () => {
      const onRetry = vi.fn()

      // Card variant
      const { unmount } = render(<ErrorDisplay variant="card" onRetry={onRetry} />)
      // unknown category default label is "Retry"
      fireEvent.click(screen.getByText('Retry'))
      expect(onRetry).toHaveBeenCalledTimes(1)
      unmount()

      // Inline variant
      onRetry.mockClear()
      render(<ErrorDisplay variant="inline" onRetry={onRetry} />)
      fireEvent.click(screen.getByText('Retry'))
      expect(onRetry).toHaveBeenCalledTimes(1)
    })

    it('retry with custom label across variants', () => {
      const onRetry = vi.fn()

      render(<ErrorDisplay variant="card" onRetry={onRetry} retryLabel="Reload Page" />)
      fireEvent.click(screen.getByText('Reload Page'))
      expect(onRetry).toHaveBeenCalledTimes(1)
    })
  })
})
