import { useState, useCallback } from 'react'

const STORAGE_KEY = 'lobster-recent-searches'
const MAX_RECENT = 5

function getStoredSearches(): string[] {
  if (typeof window === 'undefined') return []
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

export function useRecentSearches() {
  const [recentSearches, setRecentSearches] = useState<string[]>(getStoredSearches)

  const addRecentSearch = useCallback((symbol: string) => {
    const normalized = symbol.toUpperCase().trim()
    if (!normalized) return

    setRecentSearches((prev) => {
      const filtered = prev.filter((s) => s !== normalized)
      const updated = [normalized, ...filtered].slice(0, MAX_RECENT)
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
      } catch {
        // localStorage unavailable
      }
      return updated
    })
  }, [])

  const clearRecentSearches = useCallback(() => {
    setRecentSearches([])
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      // localStorage unavailable
    }
  }, [])

  return { recentSearches, addRecentSearch, clearRecentSearches }
}
