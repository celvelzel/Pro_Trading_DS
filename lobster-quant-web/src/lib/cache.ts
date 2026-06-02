/**
 * Frontend Cache Utility
 *
 * In-memory LRU cache with TTL support and optional localStorage persistence.
 * Mirrors backend/api/cache.py patterns. No external dependencies.
 *
 * Features:
 * - LRU eviction (Map maintains insertion order)
 * - Per-entry TTL expiration
 * - Namespace isolation
 * - Hit/miss statistics
 * - Optional localStorage persistence (survives page reload)
 * - Configurable max items per namespace
 */

// ============================================================================
// Types
// ============================================================================

interface CacheEntry<T = unknown> {
  value: T
  timestamp: number
  ttl: number
}

interface CacheStats {
  hits: number
  misses: number
  hitRate: number
  size: number
}

interface CacheOptions {
  /** Time-to-live in milliseconds (default: 5 min) */
  ttl?: number
  /** Whether to persist to localStorage (default: false) */
  persist?: boolean
}

interface SetOptions {
  /** Override the default TTL for this entry */
  ttl?: number
}

// ============================================================================
// Configuration
// ============================================================================

const DEFAULT_TTL = 5 * 60 * 1000 // 5 minutes
const DEFAULT_MAX_ITEMS = 500
const STORAGE_PREFIX = '__cache__'

// ============================================================================
// Cache Store
// ============================================================================

/** In-memory store: Map maintains insertion order for LRU behavior */
const store = new Map<string, Map<string, CacheEntry>>()

/** Hit/miss counters per namespace */
const hits = new Map<string, number>()
const misses = new Map<string, number>()

/** Max items per namespace */
let maxItems = DEFAULT_MAX_ITEMS

// ============================================================================
// Namespace helpers
// ============================================================================

function getNamespace(namespace: string): Map<string, CacheEntry> {
  let ns = store.get(namespace)
  if (!ns) {
    ns = new Map()
    store.set(namespace, ns)
  }
  return ns
}

function incrementHits(namespace: string): void {
  hits.set(namespace, (hits.get(namespace) ?? 0) + 1)
}

function incrementMisses(namespace: string): void {
  misses.set(namespace, (misses.get(namespace) ?? 0) + 1)
}

// ============================================================================
// Storage helpers (localStorage persistence)
// ============================================================================

function storageKey(namespace: string, key: string): string {
  return `${STORAGE_PREFIX}${namespace}:${key}`
}

function persistEntry(namespace: string, key: string, entry: CacheEntry): void {
  try {
    localStorage.setItem(
      storageKey(namespace, key),
      JSON.stringify(entry)
    )
  } catch {
    // localStorage full or unavailable — silently skip
  }
}

function loadPersistedEntry(namespace: string, key: string): CacheEntry | null {
  try {
    const raw = localStorage.getItem(storageKey(namespace, key))
    if (!raw) return null
    const entry: CacheEntry = JSON.parse(raw)
    // Check if expired
    if (Date.now() - entry.timestamp >= entry.ttl) {
      localStorage.removeItem(storageKey(namespace, key))
      return null
    }
    return entry
  } catch {
    return null
  }
}

function removePersistedEntry(namespace: string, key: string): void {
  try {
    localStorage.removeItem(storageKey(namespace, key))
  } catch {
    // Ignore
  }
}

// ============================================================================
// Public API
// ============================================================================

/**
 * Get a cached value if it exists and hasn't expired.
 *
 * Promotes accessed entries to most-recently-used position.
 * Falls back to localStorage if persist option was used.
 *
 * @param namespace - Cache namespace (e.g. "stock", "scanner")
 * @param key - Cache key (e.g. "AAPL:indicators")
 * @param options - Cache options
 * @returns Cached value or null if miss/expired
 */
export function cacheGet<T = unknown>(
  namespace: string,
  key: string,
  options: CacheOptions = {}
): T | null {
  const ns = getNamespace(namespace)
  const ttl = options.ttl ?? DEFAULT_TTL

  // Try in-memory cache first
  if (ns.has(key)) {
    const entry = ns.get(key)!
    if (Date.now() - entry.timestamp < ttl) {
      // Hit — re-insert to move to end (most recently used)
      ns.delete(key)
      ns.set(key, entry)
      incrementHits(namespace)
      return entry.value as T
    }
    // Expired — remove
    ns.delete(key)
    removePersistedEntry(namespace, key)
  }

  // Fallback: try localStorage for persisted entries
  if (options.persist) {
    const persisted = loadPersistedEntry(namespace, key)
    if (persisted) {
      // Rehydrate into memory
      ns.set(key, persisted)
      incrementHits(namespace)
      return persisted.value as T
    }
  }

  incrementMisses(namespace)
  return null
}

/**
 * Store a value in the cache with LRU eviction.
 *
 * When the namespace exceeds maxItems, the least-recently-used
 * entry is evicted automatically.
 *
 * @param namespace - Cache namespace
 * @param key - Cache key
 * @param value - Value to cache
 * @param options - Cache options
 */
export function cacheSet<T = unknown>(
  namespace: string,
  key: string,
  value: T,
  options: CacheOptions & SetOptions = {}
): void {
  const ns = getNamespace(namespace)
  const ttl = options.ttl ?? options.ttl ?? DEFAULT_TTL

  const entry: CacheEntry<T> = {
    value,
    timestamp: Date.now(),
    ttl,
  }

  // If key exists, update and move to end
  if (ns.has(key)) {
    ns.delete(key)
  } else if (ns.size >= maxItems) {
    // Evict LRU (first entry in Map)
    const firstKey = ns.keys().next().value
    if (firstKey !== undefined) {
      ns.delete(firstKey)
      removePersistedEntry(namespace, firstKey)
    }
  }

  ns.set(key, entry)

  // Optionally persist to localStorage
  if (options.persist) {
    persistEntry(namespace, key, entry)
  }
}

/**
 * Clear cache entries.
 *
 * @param namespace - If provided, clear only this namespace. Otherwise clear all.
 * @returns Number of entries cleared
 */
export function cacheClear(namespace?: string): number {
  let count = 0

  if (namespace) {
    const ns = store.get(namespace)
    if (ns) {
      count = ns.size
      // Clear localStorage entries for this namespace
      for (const key of Array.from(ns.keys())) {
        removePersistedEntry(namespace, key)
      }
      store.delete(namespace)
      hits.delete(namespace)
      misses.delete(namespace)
    }
  } else {
    // Clear all
    for (const [nsName, ns] of Array.from(store)) {
      count += ns.size
      for (const key of Array.from(ns.keys())) {
        removePersistedEntry(nsName, key)
      }
    }
    store.clear()
    hits.clear()
    misses.clear()
  }

  return count
}

/**
 * Invalidate cache entries matching a pattern.
 *
 * @param namespace - Cache namespace
 * @param keyPattern - String prefix or regex to match keys
 * @returns Number of entries invalidated
 */
export function cacheInvalidate(namespace: string, keyPattern: string | RegExp): number {
  const ns = getNamespace(namespace)
  let count = 0

  const matches =
    typeof keyPattern === 'string'
      ? (key: string) => key.startsWith(keyPattern)
      : (key: string) => keyPattern.test(key)

  for (const key of Array.from(ns.keys())) {
    if (matches(key)) {
      ns.delete(key)
      removePersistedEntry(namespace, key)
      count++
    }
  }

  return count
}

/**
 * Get hit/miss statistics per namespace.
 *
 * @param namespace - Optional specific namespace, or all if omitted
 */
export function cacheStats(namespace?: string): Record<string, CacheStats> {
  const stats: Record<string, CacheStats> = {}

  const namespaces = namespace
    ? [namespace]
    : Array.from(new Set(Array.from(store.keys()).concat(Array.from(hits.keys())).concat(Array.from(misses.keys()))))

  for (const ns of namespaces) {
    const h = hits.get(ns) ?? 0
    const m = misses.get(ns) ?? 0
    const total = h + m
    stats[ns] = {
      hits: h,
      misses: m,
      hitRate: total > 0 ? h / total : 0,
      size: store.get(ns)?.size ?? 0,
    }
  }

  return stats
}

/**
 * Set the maximum number of items per namespace.
 */
export function setMaxItems(newMax: number): void {
  if (newMax <= 0) {
    throw new Error('maxItems must be positive')
  }
  maxItems = newMax
}

/**
 * Generate a cache key from parameters.
 * Useful for building deterministic keys from query params.
 *
 * @param parts - Key parts to join
 * @returns Joined cache key
 */
export function makeCacheKey(...parts: (string | number | boolean | undefined)[]): string {
  return parts.filter((p) => p !== undefined).join(':')
}

// ============================================================================
// React Query integration helpers
// ============================================================================

/**
 * Financial data cache timing presets (matching useStock.ts).
 * Use these when creating custom cache utilities that need
 * to align with React Query's staleTime/gcTime.
 */
export const CACHE_TIMING = {
  /** Real-time price data: 30s */
  PRICE: 30 * 1000,
  /** Trading signals: 2min */
  SIGNALS: 2 * 60 * 1000,
  /** Technical indicators: 5min */
  INDICATORS: 5 * 60 * 1000,
  /** Options analysis: 5min */
  OPTIONS: 5 * 60 * 1000,
  /** Risk assessment: 5min */
  RISK: 5 * 60 * 1000,
  /** Scanner results: 1min */
  SCANNER: 1 * 60 * 1000,
  /** Backtest results: 10min */
  BACKTEST: 10 * 60 * 1000,
} as const
