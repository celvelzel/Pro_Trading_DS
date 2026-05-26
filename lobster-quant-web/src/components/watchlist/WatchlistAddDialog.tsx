'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Plus, X } from 'lucide-react'

interface WatchlistAddDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdd: (symbol: string) => void
}

const RECENT_SEARCHES_KEY = 'recentStockSearches'
const MAX_RECENT = 5

function getRecentSearches(): string[] {
  if (typeof window === 'undefined') return []
  try {
    const stored = localStorage.getItem(RECENT_SEARCHES_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

function addRecentSearch(symbol: string) {
  const recent = getRecentSearches().filter((s) => s !== symbol)
  recent.unshift(symbol)
  if (recent.length > MAX_RECENT) recent.pop()
  localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recent))
}

export function WatchlistAddDialog({
  open,
  onOpenChange,
  onAdd,
}: WatchlistAddDialogProps) {
  const [symbol, setSymbol] = useState('')
  const [recentSearches, setRecentSearches] = useState<string[]>([])

  // Load recent searches when dialog opens
  const handleOpenChange = (isOpen: boolean) => {
    if (isOpen) {
      setRecentSearches(getRecentSearches())
    }
    onOpenChange(isOpen)
  }

  const handleAdd = (sym: string) => {
    const upperSymbol = sym.trim().toUpperCase()
    if (!upperSymbol) return

    addRecentSearch(upperSymbol)
    onAdd(upperSymbol)
    setSymbol('')
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add to Watchlist</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Enter stock symbol (e.g., AAPL)"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAdd(symbol)
              }}
              autoFocus
            />
            <Button onClick={() => handleAdd(symbol)} disabled={!symbol.trim()}>
              <Plus className="w-4 h-4 mr-1" />
              Add
            </Button>
          </div>

          {recentSearches.length > 0 && (
            <div>
              <p className="text-sm text-text-secondary mb-2">Recent searches:</p>
              <div className="flex flex-wrap gap-2">
                {recentSearches.map((s) => (
                  <Button
                    key={s}
                    variant="outline"
                    size="sm"
                    onClick={() => handleAdd(s)}
                  >
                    {s}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
