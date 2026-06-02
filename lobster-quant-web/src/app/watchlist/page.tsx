'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { HelpTooltip } from '@/components/ui/help-tooltip'
import { WatchlistTable } from '@/components/watchlist/WatchlistTable'
import { WatchlistAddDialog } from '@/components/watchlist/WatchlistAddDialog'
import { StockCompareView } from '@/components/watchlist/StockCompareView'
import { useWatchlistStore } from '@/stores/watchlistStore'
import { useWatchlistData } from '@/hooks/useWatchlistData'
import { Plus, Search, List } from 'lucide-react'

export default function WatchlistPage() {
  const { symbols, addSymbol } = useWatchlistStore()
  const { stocks, isLoading, refetch } = useWatchlistData()
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [compareSymbols, setCompareSymbols] = useState<string[]>([])
  const [quickAddSymbol, setQuickAddSymbol] = useState('')

  const handleQuickAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (quickAddSymbol.trim()) {
      addSymbol(quickAddSymbol.trim())
      setQuickAddSymbol('')
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-3xl font-bold text-text-primary">Watchlist</h1>
          <HelpTooltip helpKey="dashboard.watchlist" />
        </div>
        <p className="text-text-secondary mt-1">
          Track and monitor your favorite stocks with real-time prices and signals
        </p>
      </div>

      {/* Quick Add */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Add Stock
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleQuickAdd} className="flex gap-3">
            <div className="flex-1">
              <Input
                type="text"
                placeholder="Enter stock symbol (e.g., AAPL, MSFT, TSLA)"
                value={quickAddSymbol}
                onChange={(e) => setQuickAddSymbol(e.target.value.toUpperCase())}
              />
            </div>
            <Button type="submit" disabled={!quickAddSymbol.trim()}>
              <Plus className="w-4 h-4 mr-1" />
              Add
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setAddDialogOpen(true)}
            >
              <Search className="w-4 h-4 mr-1" />
              Browse
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Stock Comparison (conditional) */}
      {compareSymbols.length > 1 && (
        <StockCompareView
          symbols={compareSymbols}
          onClose={() => setCompareSymbols([])}
        />
      )}

      {/* Watchlist Table */}
      <div className="flex items-center gap-2 mb-2">
        <List className="w-5 h-5 text-text-secondary" />
        <h2 className="text-lg font-semibold">
          Your Stocks ({symbols.length})
        </h2>
      </div>
      <WatchlistTable
        stocks={stocks}
        loading={isLoading}
        onAddClick={() => setAddDialogOpen(true)}
        onCompareClick={(syms) => setCompareSymbols(syms)}
        onRefresh={refetch}
      />

      {/* Add Dialog */}
      <WatchlistAddDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        onAdd={(symbol) => addSymbol(symbol)}
      />
    </div>
  )
}
