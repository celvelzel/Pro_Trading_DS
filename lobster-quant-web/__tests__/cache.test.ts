/**
 * Unit tests for cache.ts
 * Tests LRU cache with TTL, namespace isolation, and persistence.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  cacheGet,
  cacheSet,
  cacheClear,
  cacheInvalidate,
  cacheStats,
  setMaxItems,
  makeCacheKey,
  CACHE_TIMING,
} from '@/lib/cache'

// Clear all caches before each test
beforeEach(() => {
  cacheClear()
  setMaxItems(500) // reset to default
})

// ─── Basic Get/Set ────────────────────────────────────────────────

describe('cacheGet / cacheSet', () => {
  it('returns null for cache miss', () => {
    expect(cacheGet('test', 'missing')).toBeNull()
  })

  it('stores and retrieves a value', () => {
    cacheSet('test', 'key1', 'value1')
    expect(cacheGet('test', 'key1')).toBe('value1')
  })

  it('stores and retrieves objects', () => {
    const obj = { name: 'AAPL', price: 150 }
    cacheSet('stocks', 'AAPL', obj)
    expect(cacheGet('stocks', 'AAPL')).toEqual(obj)
  })

  it('stores and retrieves arrays', () => {
    const arr = [1, 2, 3]
    cacheSet('test', 'arr', arr)
    expect(cacheGet('test', 'arr')).toEqual(arr)
  })

  it('overwrites existing key', () => {
    cacheSet('test', 'key1', 'old')
    cacheSet('test', 'key1', 'new')
    expect(cacheGet('test', 'key1')).toBe('new')
  })
})

// ─── TTL Expiration ───────────────────────────────────────────────

describe('TTL expiration', () => {
  it('returns value before TTL expires', () => {
    cacheSet('test', 'key1', 'value1', { ttl: 10000 })
    expect(cacheGet('test', 'key1', { ttl: 10000 })).toBe('value1')
  })

  it('returns null after TTL expires', () => {
    vi.useFakeTimers()
    cacheSet('test', 'key1', 'value1', { ttl: 1000 })

    // Advance past TTL
    vi.advanceTimersByTime(1500)
    expect(cacheGet('test', 'key1', { ttl: 1000 })).toBeNull()

    vi.useRealTimers()
  })

  it('respects per-entry TTL override', () => {
    vi.useFakeTimers()
    cacheSet('test', 'short', 'val', { ttl: 500 })
    cacheSet('test', 'long', 'val', { ttl: 5000 })

    vi.advanceTimersByTime(1000)

    expect(cacheGet('test', 'short', { ttl: 500 })).toBeNull()
    expect(cacheGet('test', 'long', { ttl: 5000 })).toBe('val')

    vi.useRealTimers()
  })
})

// ─── Namespace Isolation ──────────────────────────────────────────

describe('namespace isolation', () => {
  it('keeps namespaces separate', () => {
    cacheSet('ns1', 'key', 'value1')
    cacheSet('ns2', 'key', 'value2')

    expect(cacheGet('ns1', 'key')).toBe('value1')
    expect(cacheGet('ns2', 'key')).toBe('value2')
  })

  it('clearing one namespace does not affect others', () => {
    cacheSet('ns1', 'key', 'value1')
    cacheSet('ns2', 'key', 'value2')

    cacheClear('ns1')

    expect(cacheGet('ns1', 'key')).toBeNull()
    expect(cacheGet('ns2', 'key')).toBe('value2')
  })
})

// ─── LRU Eviction ────────────────────────────────────────────────

describe('LRU eviction', () => {
  it('evicts least recently used when maxItems exceeded', () => {
    setMaxItems(3)

    cacheSet('test', 'a', 1)
    cacheSet('test', 'b', 2)
    cacheSet('test', 'c', 3)

    // All present
    expect(cacheGet('test', 'a')).toBe(1)

    // Adding 'd' should evict 'b' (LRU since 'a' was accessed)
    cacheSet('test', 'd', 4)

    expect(cacheGet('test', 'b')).toBeNull()
    expect(cacheGet('test', 'a')).toBe(1)
    expect(cacheGet('test', 'c')).toBe(3)
    expect(cacheGet('test', 'd')).toBe(4)
  })

  it('promotes accessed entries to most-recently-used', () => {
    setMaxItems(3)

    cacheSet('test', 'a', 1)
    cacheSet('test', 'b', 2)
    cacheSet('test', 'c', 3)

    // Access 'a' to promote it
    cacheGet('test', 'a')

    // Adding 'd' should evict 'b' (now LRU)
    cacheSet('test', 'd', 4)

    expect(cacheGet('test', 'a')).toBe(1)
    expect(cacheGet('test', 'b')).toBeNull()
  })

  it('setMaxItems throws for non-positive values', () => {
    expect(() => setMaxItems(0)).toThrow('maxItems must be positive')
    expect(() => setMaxItems(-1)).toThrow('maxItems must be positive')
  })
})

// ─── Cache Clear ─────────────────────────────────────────────────

describe('cacheClear', () => {
  it('clears specific namespace', () => {
    cacheSet('ns1', 'k1', 'v1')
    cacheSet('ns1', 'k2', 'v2')
    cacheSet('ns2', 'k3', 'v3')

    const count = cacheClear('ns1')
    expect(count).toBe(2)
    expect(cacheGet('ns1', 'k1')).toBeNull()
    expect(cacheGet('ns2', 'k3')).toBe('v3')
  })

  it('clears all namespaces when no argument', () => {
    cacheSet('ns1', 'k1', 'v1')
    cacheSet('ns2', 'k2', 'v2')

    const count = cacheClear()
    expect(count).toBe(2)
    expect(cacheGet('ns1', 'k1')).toBeNull()
    expect(cacheGet('ns2', 'k2')).toBeNull()
  })

  it('returns 0 for non-existent namespace', () => {
    expect(cacheClear('nonexistent')).toBe(0)
  })
})

// ─── Cache Invalidate ────────────────────────────────────────────

describe('cacheInvalidate', () => {
  it('invalidates by string prefix', () => {
    cacheSet('test', 'AAPL:price', 150)
    cacheSet('test', 'AAPL:volume', 1000)
    cacheSet('test', 'MSFT:price', 300)

    const count = cacheInvalidate('test', 'AAPL:')
    expect(count).toBe(2)
    expect(cacheGet('test', 'AAPL:price')).toBeNull()
    expect(cacheGet('test', 'MSFT:price')).toBe(300)
  })

  it('invalidates by regex pattern', () => {
    cacheSet('test', 'key-1', 'a')
    cacheSet('test', 'key-2', 'b')
    cacheSet('test', 'other', 'c')

    const count = cacheInvalidate('test', /^key-/)
    expect(count).toBe(2)
    expect(cacheGet('test', 'other')).toBe('c')
  })

  it('returns 0 when no matches', () => {
    cacheSet('test', 'key', 'val')
    expect(cacheInvalidate('test', 'zzz')).toBe(0)
  })
})

// ─── Cache Stats ─────────────────────────────────────────────────

describe('cacheStats', () => {
  it('tracks hits and misses', () => {
    cacheSet('test', 'k1', 'v1')
    cacheGet('test', 'k1') // hit
    cacheGet('test', 'k1') // hit
    cacheGet('test', 'missing') // miss

    const stats = cacheStats('test')
    expect(stats.test.hits).toBe(2)
    expect(stats.test.misses).toBe(1)
    expect(stats.test.hitRate).toBeCloseTo(2 / 3)
    expect(stats.test.size).toBe(1)
  })

  it('returns stats for all namespaces', () => {
    cacheSet('a', 'k', 'v')
    cacheSet('b', 'k', 'v')
    cacheGet('a', 'k')

    const stats = cacheStats()
    expect(stats.a).toBeDefined()
    expect(stats.b).toBeDefined()
    expect(stats.a.hits).toBe(1)
  })

  it('returns zero stats for empty namespace', () => {
    const stats = cacheStats('empty')
    expect(stats.empty.hits).toBe(0)
    expect(stats.empty.misses).toBe(0)
    expect(stats.empty.hitRate).toBe(0)
    expect(stats.empty.size).toBe(0)
  })
})

// ─── makeCacheKey ────────────────────────────────────────────────

describe('makeCacheKey', () => {
  it('joins parts with colon', () => {
    expect(makeCacheKey('AAPL', 'indicators')).toBe('AAPL:indicators')
  })

  it('filters out undefined values', () => {
    expect(makeCacheKey('AAPL', undefined, 'price')).toBe('AAPL:price')
  })

  it('handles numbers and booleans', () => {
    expect(makeCacheKey('test', 42, true)).toBe('test:42:true')
  })

  it('returns empty string for all undefined', () => {
    expect(makeCacheKey(undefined, undefined)).toBe('')
  })
})

// ─── CACHE_TIMING presets ────────────────────────────────────────

describe('CACHE_TIMING', () => {
  it('has correct timing values', () => {
    expect(CACHE_TIMING.PRICE).toBe(30_000)
    expect(CACHE_TIMING.SIGNALS).toBe(120_000)
    expect(CACHE_TIMING.INDICATORS).toBe(300_000)
    expect(CACHE_TIMING.SCANNER).toBe(60_000)
    expect(CACHE_TIMING.BACKTEST).toBe(600_000)
  })
})
