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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Plus, ListPlus } from 'lucide-react'
import { useSyncWatchlist } from '@/stores/watchlistStore'

interface WatchlistAddDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
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
}: WatchlistAddDialogProps) {
  const { addSymbol, bulkAddSymbols, groups } = useSyncWatchlist()
  const [symbol, setSymbol] = useState('')
  const [bulkSymbols, setBulkSymbols] = useState('')
  const [selectedGroup, setSelectedGroup] = useState<string>('none')
  const [recentSearches, setRecentSearches] = useState<string[]>([])

  const groupNames = Object.keys(groups).sort()

  // Load recent searches when dialog opens
  const handleOpenChange = (isOpen: boolean) => {
    if (isOpen) {
      setRecentSearches(getRecentSearches())
    }
    onOpenChange(isOpen)
  }

  const handleAddSingle = () => {
    const upperSymbol = symbol.trim().toUpperCase()
    if (!upperSymbol) return

    addRecentSearch(upperSymbol)
    addSymbol(upperSymbol)
    
    // If a group is selected, we need to add it to the group too
    // Note: addSymbol only adds to the master list in the current implementation
    // We might want to update the store to handle this, or call addToGroup
    if (selectedGroup !== 'none') {
      // The backend bulk endpoint handles this better, let's use it even for single if group is selected
      bulkAddSymbols([upperSymbol], selectedGroup)
    }

    setSymbol('')
    onOpenChange(false)
  }

  const handleAddRecent = (sym: string) => {
    if (selectedGroup !== 'none') {
      bulkAddSymbols([sym], selectedGroup)
    } else {
      addSymbol(sym)
    }
    onOpenChange(false)
  }

  const handleAddBulk = () => {
    const symbols = bulkSymbols
      .split(/[\n,]+/)
      .map((s) => s.trim().toUpperCase())
      .filter((s) => s.length > 0)

    if (symbols.length === 0) return

    bulkAddSymbols(symbols, selectedGroup === 'none' ? undefined : selectedGroup)
    setBulkSymbols('')
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add to Watchlist</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="single" className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-4">
            <TabsTrigger value="single">Single Stock</TabsTrigger>
            <TabsTrigger value="bulk">Bulk Add</TabsTrigger>
          </TabsList>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Target Group (Optional)
              </label>
              <Select value={selectedGroup} onValueChange={setSelectedGroup}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a group" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No Group (Main List)</SelectItem>
                  {groupNames.map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <TabsContent value="single" className="space-y-4 mt-0">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter stock symbol (e.g., AAPL)"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAddSingle()
                  }}
                  autoFocus
                />
                <Button onClick={handleAddSingle} disabled={!symbol.trim()}>
                  <Plus className="w-4 h-4 mr-1" />
                  Add
                </Button>
              </div>

              {recentSearches.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-2">Recent Searches</p>
                  <div className="flex flex-wrap gap-2">
                    {recentSearches.map((s) => (
                      <button
                        key={s}
                        onClick={() => handleAddRecent(s)}
                        className="text-xs px-2 py-1 rounded bg-muted hover:bg-muted/80 transition-colors"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="bulk" className="space-y-4 mt-0">
              <div className="space-y-2">
                <textarea
                  placeholder="Paste symbols separated by commas or new lines (e.g., AAPL, MSFT, TSLA)"
                  value={bulkSymbols}
                  onChange={(e) => setBulkSymbols(e.target.value.toUpperCase())}
                  className="w-full min-h-[120px] rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
                />
                <Button 
                  onClick={handleAddBulk} 
                  disabled={!bulkSymbols.trim()}
                  className="w-full"
                >
                  <ListPlus className="w-4 h-4 mr-2" />
                  Add {bulkSymbols.split(/[\n,]+/).filter(s => s.trim()).length} Symbols
                </Button>
              </div>
            </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
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
