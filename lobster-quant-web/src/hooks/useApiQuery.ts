'use client'

import { useCallback, useEffect } from 'react'
import {
  useQuery,
  type QueryKey,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import type { ApiError } from '@/lib/types'

// ============================================================================
// Error Classification
// ============================================================================

type ErrorCategory = 'network' | 'not_found' | 'server' | 'unknown'

function classifyError(error: unknown): ErrorCategory {
  if (!error) return 'unknown'

  // Network errors (fetch failures, CORS, etc.)
  if (error instanceof TypeError && error.message === 'Failed to fetch') {
    return 'network'
  }

  // ApiError from our API client
  if (typeof error === 'object' && error !== null && 'status' in error) {
    const status = (error as ApiError).status
    if (status === 404) return 'not_found'
    if (status >= 500) return 'server'
  }

  return 'unknown'
}

function getErrorTitle(category: ErrorCategory): string {
  switch (category) {
    case 'network':
      return 'Connection Error'
    case 'not_found':
      return 'Not Found'
    case 'server':
      return 'Server Error'
    default:
      return 'Something went wrong'
  }
}

function getErrorMessage(error: unknown, category: ErrorCategory): string {
  // Use API error detail if available
  if (typeof error === 'object' && error !== null && 'detail' in error) {
    return (error as ApiError).detail
  }

  switch (category) {
    case 'network':
      return 'Unable to connect to the server. Please check your connection and try again.'
    case 'not_found':
      return 'The requested resource was not found.'
    case 'server':
      return 'A server error occurred. Please try again later.'
    default:
      if (error instanceof Error) {
        return error.message
      }
      return 'An unexpected error occurred.'
  }
}

// ============================================================================
// Toast Error Handler
// ============================================================================

export function showToastError(error: unknown): void {
  const category = classifyError(error)
  const message = getErrorMessage(error, category)

  toast.error(message, {
    duration: 5000,
    action: category === 'network' ? {
      label: 'Retry',
      onClick: () => window.location.reload(),
    } : undefined,
  })
}

// ============================================================================
// useApiQuery Hook
// ============================================================================

interface UseApiQueryOptions<TQueryFnData = unknown, TData = TQueryFnData> {
  queryKey: QueryKey
  queryFn: () => Promise<TQueryFnData>
  /** Whether the query is enabled */
  enabled?: boolean
  /** Stale time in milliseconds */
  staleTime?: number
  /** GC time in milliseconds */
  gcTime?: number
  /** Select/transform the data */
  select?: (data: TQueryFnData) => TData
  /** Suppress toast notifications for errors (useful when rendering inline ErrorState) */
  suppressToast?: boolean
}

interface ErrorInfo {
  /** User-friendly error title */
  title: string
  /** User-friendly error message */
  message: string
  /** Error category for conditional rendering */
  category: ErrorCategory
  /** Retry callback */
  onRetry: () => void
}

interface UseApiQueryResult<TData = unknown> {
  data: TData | undefined
  isLoading: boolean
  error: unknown
  /** Structured error info for rendering custom error UI. Null when no error. */
  errorInfo: ErrorInfo | null
  /** Manually trigger a refetch */
  refetch: () => Promise<unknown>
  /** Whether the query has data */
  isSuccess: boolean
  /** Whether the query is in an error state */
  isError: boolean
}

export function useApiQuery<TQueryFnData = unknown, TData = TQueryFnData>(
  options: UseApiQueryOptions<TQueryFnData, TData>
): UseApiQueryResult<TData> {
  const { suppressToast = false, ...queryOptions } = options

  const queryResult = useQuery({
    queryKey: queryOptions.queryKey,
    queryFn: queryOptions.queryFn,
    enabled: queryOptions.enabled,
    staleTime: queryOptions.staleTime,
    gcTime: queryOptions.gcTime,
    select: queryOptions.select as ((data: TQueryFnData) => TData) | undefined,
  })

  const { data, isLoading, error, refetch, isSuccess, isError } = queryResult

  // Show toast on error (unless suppressed)
  useEffect(() => {
    if (isError && error && !suppressToast) {
      showToastError(error)
    }
  }, [isError, error, suppressToast])

  // Memoize retry handler
  const handleRetry = useCallback(() => {
    refetch()
  }, [refetch])

  // Build error info when there's an error and no data
  const errorInfo: ErrorInfo | null = isError && error && !isLoading
    ? {
        category: classifyError(error),
        title: getErrorTitle(classifyError(error)),
        message: getErrorMessage(error, classifyError(error)),
        onRetry: handleRetry,
      }
    : null

  return {
    data,
    isLoading,
    error,
    errorInfo,
    refetch,
    isSuccess,
    isError,
  }
}

// ============================================================================
// Convenience Exports
// ============================================================================

/**
 * Helper to get a user-friendly error message from any error.
 * Useful for inline error display outside of ErrorState.
 */
export function getApiErrorMessage(error: unknown): string {
  const category = classifyError(error)
  return getErrorMessage(error, category)
}
