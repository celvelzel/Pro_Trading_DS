'use client'

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Clock, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { STOCK_LISTS } from '@/lib/constants'
import { useDebounce } from '@/hooks/useDebounce'
import { useRecentSearches } from '@/hooks/useRecentSearches'

// Flatten all stocks into a single list
const ALL_STOCKS = Object.entries(STOCK_LISTS).flatMap(([market, symbols]) =>
  symbols.map((symbol) => ({ symbol, market }))
)

interface SuggestionItem {
  symbol: string
  market: string
  type: 'recent' | 'match'
}

export function SearchAutocomplete() {
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const debouncedQuery = useDebounce(query, 300)
  const { recentSearches, addRecentSearch, clearRecentSearches } = useRecentSearches()

  // Build suggestion list
  const suggestions = useMemo<SuggestionItem[]>(() => {
    const trimmed = debouncedQuery.trim().toUpperCase()

    if (!trimmed) {
      // Show recent searches when no query
      return recentSearches.map((symbol) => {
        const stock = ALL_STOCKS.find((s) => s.symbol === symbol)
        return { symbol, market: stock?.market ?? '', type: 'recent' as const }
      })
    }

    // Prefix match first, then contains match, deduplicated
    const prefixMatches: SuggestionItem[] = []
    const containsMatches: SuggestionItem[] = []

    for (const stock of ALL_STOCKS) {
      const upper = stock.symbol.toUpperCase()
      if (upper.startsWith(trimmed)) {
        prefixMatches.push({ ...stock, type: 'match' })
      } else if (upper.includes(trimmed)) {
        containsMatches.push({ ...stock, type: 'match' })
      }
    }

    return [...prefixMatches, ...containsMatches].slice(0, 8)
  }, [debouncedQuery, recentSearches])

  const hasSuggestions = suggestions.length > 0

  // Navigate to stock
  const navigateToStock = useCallback(
    (symbol: string) => {
      const normalized = symbol.toUpperCase().trim()
      if (!normalized) return
      addRecentSearch(normalized)
      router.push(`/analysis/${normalized}`)
      setQuery('')
      setIsOpen(false)
      setActiveIndex(-1)
      inputRef.current?.blur()
    },
    [addRecentSearch, router]
  )

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
        setActiveIndex(-1)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Scroll active item into view
  useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const item = listRef.current.children[activeIndex] as HTMLElement | undefined
      item?.scrollIntoView({ block: 'nearest' })
    }
  }, [activeIndex])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        if (hasSuggestions) {
          setIsOpen(true)
          setActiveIndex(0)
          e.preventDefault()
        }
      }
      return
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setActiveIndex((prev) => (prev + 1) % suggestions.length)
        break
      case 'ArrowUp':
        e.preventDefault()
        setActiveIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length)
        break
      case 'Enter':
        e.preventDefault()
        if (activeIndex >= 0 && activeIndex < suggestions.length) {
          navigateToStock(suggestions[activeIndex].symbol)
        } else if (query.trim()) {
          navigateToStock(query)
        }
        break
      case 'Escape':
        e.preventDefault()
        setIsOpen(false)
        setActiveIndex(-1)
        inputRef.current?.blur()
        break
      case 'Tab':
        setIsOpen(false)
        setActiveIndex(-1)
        break
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
    setIsOpen(true)
    setActiveIndex(-1)
  }

  const handleFocus = () => {
    setIsOpen(true)
  }

  const handleClearQuery = () => {
    setQuery('')
    setActiveIndex(-1)
    inputRef.current?.focus()
  }

  const showDropdown = isOpen && hasSuggestions

  return (
    <div ref={containerRef} className="relative flex-1 max-w-md">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (query.trim()) navigateToStock(query)
        }}
        className="relative"
      >
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
        <Input
          ref={inputRef}
          type="search"
          placeholder="Search stock symbol (e.g., AAPL)..."
          className="pl-8 pr-8"
          value={query}
          onChange={handleInputChange}
          onFocus={handleFocus}
          onKeyDown={handleKeyDown}
          role="combobox"
          aria-expanded={showDropdown}
          aria-autocomplete="list"
          aria-controls="search-suggestions"
          aria-activedescendant={
            activeIndex >= 0 ? `suggestion-${activeIndex}` : undefined
          }
          autoComplete="off"
        />
        {query && (
          <button
            type="button"
            onClick={handleClearQuery}
            className="absolute right-2.5 top-2.5 h-4 w-4 text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </form>

      {/* Dropdown */}
      {showDropdown && (
        <ul
          ref={listRef}
          id="search-suggestions"
          role="listbox"
          className={cn(
            'absolute top-full left-0 right-0 z-50 mt-1 max-h-64 overflow-auto',
            'rounded-lg border bg-popover p-1 shadow-md',
            'animate-in fade-in-0 zoom-in-95'
          )}
        >
          {/* Recent header */}
          {!debouncedQuery.trim() && recentSearches.length > 0 && (
            <li className="flex items-center justify-between px-2 py-1.5">
              <span className="text-xs font-medium text-muted-foreground">Recent searches</span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  clearRecentSearches()
                }}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Clear
              </button>
            </li>
          )}

          {suggestions.map((item, index) => (
            <li
              key={`${item.type}-${item.symbol}`}
              id={`suggestion-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              className={cn(
                'flex items-center gap-2 rounded-md px-2 py-1.5 cursor-pointer text-sm',
                'transition-colors select-none',
                index === activeIndex
                  ? 'bg-accent text-accent-foreground'
                  : 'hover:bg-accent/50'
              )}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseDown={(e) => {
                // Prevent blur on the input
                e.preventDefault()
              }}
              onClick={() => navigateToStock(item.symbol)}
            >
              {item.type === 'recent' ? (
                <Clock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              ) : (
                <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              )}
              <span className="font-medium">{item.symbol}</span>
              {item.market && (
                <span className="ml-auto text-xs text-muted-foreground">{item.market}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
