/**
 * Unit tests for error-messages.ts
 * Tests error categorization and message lookup.
 */
import { describe, it, expect } from 'vitest'
import { categorizeError, ERROR_MESSAGES, type ErrorCategory } from '@/lib/error-messages'

// ─── categorizeError ─────────────────────────────────────────────

describe('categorizeError', () => {
  it('returns "unknown" for null/undefined', () => {
    expect(categorizeError(null)).toBe('unknown')
    expect(categorizeError(undefined)).toBe('unknown')
  })

  // Network errors
  it('categorizes network errors by message', () => {
    expect(categorizeError({ message: 'Network request failed' })).toBe('network')
    expect(categorizeError({ message: 'fetch failed' })).toBe('network')
    expect(categorizeError({ message: 'Failed to fetch' })).toBe('network')
  })

  // Auth errors
  it('categorizes auth errors by status code', () => {
    expect(categorizeError({ code: 401 })).toBe('auth')
    expect(categorizeError({ code: 403 })).toBe('auth')
    expect(categorizeError({ status: 401 })).toBe('auth')
  })

  it('categorizes auth errors by message', () => {
    expect(categorizeError({ message: 'Unauthorized access' })).toBe('auth')
    expect(categorizeError({ message: 'Forbidden resource' })).toBe('auth')
  })

  // Timeout errors
  it('categorizes timeout errors by status code', () => {
    expect(categorizeError({ code: 504 })).toBe('timeout')
    expect(categorizeError({ code: 408 })).toBe('timeout')
  })

  it('categorizes timeout errors by message', () => {
    expect(categorizeError({ message: 'Request timeout exceeded' })).toBe('timeout')
  })

  // Validation errors
  it('categorizes validation errors by status code', () => {
    expect(categorizeError({ code: 400 })).toBe('validation')
    expect(categorizeError({ code: 422 })).toBe('validation')
  })

  it('categorizes validation errors by message', () => {
    expect(categorizeError({ message: 'Invalid input data' })).toBe('validation')
    expect(categorizeError({ message: 'Validation failed' })).toBe('validation')
  })

  // Market errors
  it('categorizes market errors by message', () => {
    expect(categorizeError({ message: 'Market data unavailable' })).toBe('market')
    expect(categorizeError({ message: 'ticker not found' })).toBe('market')
    expect(categorizeError({ message: 'Price data not found' })).toBe('market')
  })

  // API errors
  it('categorizes server errors by status code >= 500', () => {
    expect(categorizeError({ code: 500 })).toBe('api')
    expect(categorizeError({ code: 502 })).toBe('api')
    expect(categorizeError({ code: 503 })).toBe('api')
  })

  // Unknown errors
  it('returns "unknown" for unrecognized errors', () => {
    expect(categorizeError({ message: 'Something weird happened' })).toBe('unknown')
    expect(categorizeError({ code: 418 })).toBe('unknown') // I'm a teapot
  })

  it('handles string errors gracefully', () => {
    // Strings don't have .message or .code, so they fall to unknown
    expect(categorizeError('some error')).toBe('unknown')
  })
})

// ─── ERROR_MESSAGES completeness ─────────────────────────────────

describe('ERROR_MESSAGES', () => {
  const categories: ErrorCategory[] = [
    'network', 'auth', 'api', 'validation', 'market', 'timeout', 'unknown',
  ]

  it.each(categories)('has messages for "%s" category', (cat) => {
    const msg = ERROR_MESSAGES[cat]
    expect(msg).toBeDefined()
    expect(msg.title.en).toBeTruthy()
    expect(msg.title.zh).toBeTruthy()
    expect(msg.message.en).toBeTruthy()
    expect(msg.message.zh).toBeTruthy()
  })

  it('has action text for categories that need retry', () => {
    const withActions: ErrorCategory[] = ['network', 'auth', 'api', 'market', 'timeout']
    for (const cat of withActions) {
      expect(ERROR_MESSAGES[cat].action).toBeDefined()
      expect(ERROR_MESSAGES[cat].action!.en).toBeTruthy()
      expect(ERROR_MESSAGES[cat].action!.zh).toBeTruthy()
    }
  })

  it('validation and unknown have no action text', () => {
    expect(ERROR_MESSAGES.validation.action).toBeUndefined()
    expect(ERROR_MESSAGES.unknown.action).toBeUndefined()
  })
})
