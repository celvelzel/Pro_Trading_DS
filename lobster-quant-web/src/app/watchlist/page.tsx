'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { HelpTooltip } from '@/components/ui/help-tooltip'
import { PageHeader } from '@/components/layout/PageHeader'
import { WatchlistTable } from '@/components/watchlist/WatchlistTable'
import { WatchlistAddDialog } from '@/components/watchlist/WatchlistAddDialog'
import { StockCompareView } from '@/components/watchlist/StockCompareView'
import { useSyncWatchlist } from '@/stores/watchlistStore'
import { useWatchlistData } from '@/hooks/useWatchlistData'
import { Plus, Search, List } from 'lucide-react'

export default function WatchlistPage() {
  const { symbols, addSymbol } = useSyncWatchlist()
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
    <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
      {/* Page Header */}
      <PageHeader
        title="Watchlist"
        description="Track and monitor your favorite stocks with real-time prices and signals"
        actions={<HelpTooltip helpKey="dashboard.watchlist" />}
      />

      {/* Quick Add — compact toolbar row */}
      <Card>
        <CardHeader className="pb-0">
          <CardTitle className="flex items-center gap-2">
            <Plus className="size-4 text-muted-foreground" />
            Add Stock
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleQuickAdd}
            className="flex flex-col gap-2 sm:flex-row sm:items-center"
          >
            <Input
              type="text"
              placeholder="Enter stock symbol (e.g., AAPL, MSFT, TSLA)"
              value={quickAddSymbol}
              onChange={(e) => setQuickAddSymbol(e.target.value.toUpperCase())}
              className="flex-1 font-mono uppercase"
            />
            <div className="flex shrink-0 items-center gap-2">
              <Button type="submit" disabled={!quickAddSymbol.trim()}>
                <Plus />
                Add
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setAddDialogOpen(true)}
              >
                <Search />
                Browse
              </Button>
            </div>
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
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <List className="size-4 text-muted-foreground" />
          <h2 className="text-base font-semibold tracking-tight text-foreground">
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
      </div>

      {/* Add Dialog */}
      <WatchlistAddDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
      />
    </div>
  )
}
