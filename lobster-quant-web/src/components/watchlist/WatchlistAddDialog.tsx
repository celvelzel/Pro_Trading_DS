'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
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
          <TabsList className="mb-1 grid w-full grid-cols-2">
            <TabsTrigger value="single">Single Stock</TabsTrigger>
            <TabsTrigger value="bulk">Bulk Add</TabsTrigger>
          </TabsList>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Target Group (Optional)
              </label>
              <Select
                value={selectedGroup}
                onValueChange={(value) => setSelectedGroup(value ?? 'none')}
              >
                <SelectTrigger className="w-full">
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

            <TabsContent value="single" className="mt-0 space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter stock symbol (e.g., AAPL)"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAddSingle()
                  }}
                  className="flex-1 font-mono uppercase"
                  autoFocus
                />
                <Button onClick={handleAddSingle} disabled={!symbol.trim()}>
                  <Plus />
                  Add
                </Button>
              </div>

              {recentSearches.length > 0 && (
                <div>
                  <p className="mb-2 text-xs text-muted-foreground">Recent Searches</p>
                  <div className="flex flex-wrap gap-2">
                    {recentSearches.map((s) => (
                      <button
                        key={s}
                        onClick={() => handleAddRecent(s)}
                        className="rounded-md border border-border bg-muted px-2 py-1 font-mono text-xs text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="bulk" className="mt-0 space-y-4">
              <div className="space-y-2">
                <Textarea
                  placeholder="Paste symbols separated by commas or new lines (e.g., AAPL, MSFT, TSLA)"
                  value={bulkSymbols}
                  onChange={(e) => setBulkSymbols(e.target.value.toUpperCase())}
                  className="min-h-[120px] w-full font-mono uppercase"
                />
                <Button
                  onClick={handleAddBulk}
                  disabled={!bulkSymbols.trim()}
                  className="w-full"
                >
                  <ListPlus />
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
