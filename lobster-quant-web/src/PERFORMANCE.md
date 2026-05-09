# Performance Optimization Documentation

## Overview

This document records the performance optimizations applied to the Lobster Quant trading platform frontend, including which components were memoized and why, cache timing rationale, and how to verify prefetching behavior.

---

## 1. React.memo — Memoized Components

### `CandlestickChart` (`src/components/charts/CandlestickChart.tsx`)

**Why memoized:** This is the most expensive component in the app. It:
- Creates a Lightweight Charts instance (canvas-based rendering)
- Sets up candlestick + volume series
- Maps potentially hundreds of OHLCV data points
- Attaches resize event listeners

**Without memo:** Every parent re-render (e.g., price update, signal change, unrelated state change) would destroy and recreate the entire chart canvas, causing visible flicker and high CPU usage.

**With memo:** The chart only re-renders when its props actually change (`data`, `symbol`, `height`, `showVolume`). Since React Query returns stable references for cached data, the chart stays stable when unrelated data updates.

### Components NOT memoized (intentionally)

- `MetricCard`, `StatusCard`, `SignalCard` — Simple presentational components with minimal render cost. Memoizing them would add overhead (comparison logic) without meaningful savings.
- `Button`, `Card`, `Input`, etc. — UI primitives that render in <1ms. Memoizing would be premature optimization.

---

## 2. React Query `select` Transforms

### `useStockCandles(symbol)` — Chart-only data

```typescript
const selectCandles = (data: StockData) => data.candles
```

**Purpose:** Extracts only the `candles` array from the full `StockData` response. When the stock's price or metadata changes but candles don't, the chart component receives the same reference and skips re-render.

**Used in:** `AnalysisDetailPage` for the price chart.

### `useStockPriceSummary(symbol)` — Lightweight display

```typescript
const selectPriceSummary = (data: StockData) => ({
  symbol, name, price, change, changePercent, volume
})
```

**Purpose:** Strips the large `candles` array (potentially 100s of KB) for components that only need price/metadata. Reduces memory and prevents re-renders when candle data updates.

**Available for:** Dashboard metric cards, watchlist displays, any component that doesn't need chart data.

---

## 3. Cache Timing Configuration

Financial data has different freshness requirements. The `CACHE_TIMING` constant in `useStock.ts` configures per-domain cache behavior:

| Data Type | `staleTime` | `gcTime` | Rationale |
|-----------|-------------|----------|-----------|
| **Price/OHLCV** | 30s | 5min | Prices change every second during market hours. 30s prevents request waterfalls while staying reasonably fresh. |
| **Signals** | 2min | 10min | Signals are derived from indicators, update less frequently than raw prices. |
| **Indicators** | 5min | 15min | RSI, MACD, MAs are calculated values that change slowly. |
| **Options** | 5min | 15min | Options data (max pain, put/call ratio) updates infrequently. |
| **Risk** | 5min | 15min | Risk assessment is a derived metric, not real-time. |
| **Scanner** | 1min | 5min | Scanner results are snapshots; 1min prevents re-scanning on quick back-navigation. |
| **Backtest** | 10min | 30min | Backtests are expensive to compute; cache aggressively. |

**Default (QueryProvider):** 2min staleTime, 10min gcTime — acts as a fallback for any query without explicit timing.

**Why not `staleTime: 0` everywhere:** This would cause every component mount to refetch all data, creating request waterfalls that overwhelm the backend and slow down navigation.

---

## 4. Prefetching on Hover

### `PrefetchLink` component (`src/components/ui/prefetch-link.tsx`)

A drop-in replacement for Next.js `<Link>` that prefetches all stock-related data on hover/focus:

- Stock OHLCV data
- Technical indicators
- Trading signals
- Options analysis
- Risk assessment

**How it works:**
1. User hovers over a stock link (e.g., in scanner results or dashboard)
2. `onMouseEnter` fires, calling `usePrefetchStock()` which prefetches all 5 data types
3. React Query caches the responses under the appropriate query keys
4. When user clicks and navigates to the analysis page, all data is already in cache
5. The analysis page renders instantly with no loading spinners

**Where it's used:**
- `DashboardPage` — Quick access stock links
- `AnalysisPage` — Quick access stock cards
- `ScannerPage` — Result cards (via inline `onMouseEnter`)

### How to verify prefetching

1. Open Chrome DevTools → Network tab
2. Hover over any stock link (e.g., AAPL on the dashboard)
3. You should see 5 requests fire immediately:
   - `GET /api/stocks/AAPL`
   - `GET /api/stocks/AAPL/indicators`
   - `GET /api/stocks/AAPL/signals`
   - `GET /api/stocks/AAPL/options`
   - `GET /api/stocks/AAPL/risk`
4. Click the link — the analysis page should load with **no additional network requests** (data is served from React Query cache)

---

## 5. Virtualization (Scanner Table)

### Implementation (`src/app/scanner/page.tsx`)

Uses `@tanstack/react-virtual` for the scanner results grid when results exceed 50 items.

**How it works:**
- Below 50 results: Standard CSS grid layout (no virtualization overhead)
- Above 50 results: Virtualized list with:
  - `estimateSize: 180px` per row (card height estimate)
  - `overscan: 5` extra rows rendered above/below viewport
  - Scroll container fixed at `70vh` height
  - Only visible rows are rendered in the DOM

**Benefits:**
- Scanner with 200+ results renders only ~10-15 cards at a time
- Smooth 60fps scrolling even with large result sets
- Reduced DOM node count → lower memory usage and faster interactions

---

## Summary of Changes

| File | Change | Impact |
|------|--------|--------|
| `src/hooks/useStock.ts` | Added `CACHE_TIMING`, `useStockCandles`, `useStockPriceSummary`, enhanced `usePrefetchStock` | Domain-specific cache timing, select transforms, full-data prefetching |
| `src/components/charts/CandlestickChart.tsx` | Wrapped in `React.memo` | Prevents chart re-renders on unrelated data changes |
| `src/components/ui/prefetch-link.tsx` | New component | Hover-prefetch for instant navigation |
| `src/providers/QueryProvider.tsx` | Updated defaults | 2min staleTime, disabled refetchOnReconnect |
| `src/app/scanner/page.tsx` | Added virtualization, prefetching | Smooth scrolling for 50+ results, instant navigation |
| `src/app/dashboard/page.tsx` | Added `PrefetchLink` for quick access | Prefetches on hover |
| `src/app/analysis/page.tsx` | Added `PrefetchLink` for quick access | Prefetches on hover |
| `src/app/analysis/[symbol]/page.tsx` | Uses `useStockCandles` with select | Chart only re-renders when candles change |
| `src/lib/types.ts` | Added `probability` to `StockResult` | Type fix for scanner results |
