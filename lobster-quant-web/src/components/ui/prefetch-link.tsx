'use client'

import Link from 'next/link'
import { useCallback, type ComponentProps } from 'react'
import { usePrefetchStock } from '@/hooks/useStock'

interface PrefetchLinkProps extends Omit<ComponentProps<typeof Link>, 'onMouseEnter' | 'onFocus'> {
  /** Stock symbol to prefetch on hover/focus */
  symbol: string
  /** Disable prefetching (e.g., for external links) */
  disablePrefetch?: boolean
}

/**
 * A Next.js Link component that prefetches all stock data on hover/focus.
 *
 * When a user hovers over or focuses a stock link, all related data
 * (OHLCV, indicators, signals, options, risk) is fetched and cached
 * before navigation, making the target page load instantly.
 *
 * @example
 * <PrefetchLink symbol="AAPL" href="/analysis/AAPL">
 *   View AAPL Analysis
 * </PrefetchLink>
 */
export function PrefetchLink({
  symbol,
  disablePrefetch = false,
  children,
  ...linkProps
}: PrefetchLinkProps) {
  const prefetchStock = usePrefetchStock()

  const handlePrefetch = useCallback(() => {
    if (!disablePrefetch) {
      prefetchStock(symbol)
    }
  }, [symbol, disablePrefetch, prefetchStock])

  return (
    <Link
      {...linkProps}
      onMouseEnter={handlePrefetch}
      onFocus={handlePrefetch}
    >
      {children}
    </Link>
  )
}
