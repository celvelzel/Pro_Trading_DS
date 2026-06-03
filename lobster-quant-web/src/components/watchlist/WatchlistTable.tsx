'use client'

import { memo, useState, useMemo } from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu'
import { useSyncWatchlist } from '@/stores/watchlistStore'
import type { WatchlistStockData } from '@/hooks/useWatchlistData'
import { ManageTagsDialog } from './ManageTagsDialog'
import { ManageGroupsDialog } from './ManageGroupsDialog'
import {
  TrendingUp,
  TrendingDown,
  Trash2,
  BarChart3,
  Plus,
  RefreshCw,
  AlertCircle,
  MoreHorizontal,
  FolderPlus,
  Tag,
  Filter,
  FolderOpen,
} from 'lucide-react'

interface WatchlistTableProps {
  stocks: WatchlistStockData[]
  loading?: boolean
  onAddClick?: () => void
  onCompareClick?: (symbols: string[]) => void
  onRefresh?: () => void
  className?: string
}

function SignalBadge({ type, score }: { type: string; score: number }) {
  const config = {
    bullish: { color: 'text-success bg-success/10', label: 'Bullish' },
    bearish: { color: 'text-error bg-error/10', label: 'Bearish' },
    neutral: { color: 'text-warning bg-warning/10', label: 'Neutral' },
  }

  const { color } = config[type as keyof typeof config] || config.neutral

  return (
    <span className={cn('px-2 py-1 rounded-full text-xs font-medium', color)}>
      {score}
    </span>
  )
}

function PriceChange({ change, changePercent }: { change?: number; changePercent?: number }) {
  if (change === undefined || changePercent === undefined) {
    return <span className="text-text-tertiary text-sm">--</span>
  }

  const isPositive = change >= 0
  const Icon = isPositive ? TrendingUp : TrendingDown

  return (
    <div className={cn('flex items-center gap-1', isPositive ? 'text-success' : 'text-error')}>
      <Icon className="w-3 h-3" />
      <span className="text-sm font-medium">
        {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
      </span>
    </div>
  )
}

function StockRowSkeleton() {
  return (
    <div className="flex items-center gap-4 py-3 animate-pulse">
      <div className="h-4 w-4 bg-muted rounded" />
      <div className="h-4 w-16 bg-muted rounded" />
      <div className="flex-1" />
      <div className="h-4 w-24 bg-muted rounded" />
      <div className="h-4 w-20 bg-muted rounded" />
      <div className="h-6 w-12 bg-muted rounded-full" />
    </div>
  )
}

function StockRowActions({ symbol }: { symbol: string }) {
  const { groups, addToGroup, removeFromGroup } = useSyncWatchlist()
  const [tagsDialogOpen, setTagsDialogOpen] = useState(false)
  const groupNames = Object.keys(groups).sort()

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <button
              className="p-1 rounded-md hover:bg-muted transition-colors"
              aria-label={`Actions for ${symbol}`}
            />
          }
        >
          <MoreHorizontal className="w-4 h-4 text-text-tertiary" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" sideOffset={4}>
          <DropdownMenuLabel>Actions</DropdownMenuLabel>
          <DropdownMenuSeparator />

          {/* Group assignment submenu */}
          {groupNames.length > 0 && (
            <>
              <DropdownMenuLabel inset>Add to Group</DropdownMenuLabel>
              {groupNames.map((groupName) => {
                const isInGroup = (groups[groupName] || []).includes(symbol)
                return (
                  <DropdownMenuCheckboxItem
                    key={groupName}
                    checked={isInGroup}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        addToGroup(groupName, symbol)
                      } else {
                        removeFromGroup(groupName, symbol)
                      }
                    }}
                  >
                    {groupName}
                  </DropdownMenuCheckboxItem>
                )
              })}
              <DropdownMenuSeparator />
            </>
          )}

          <DropdownMenuItem onClick={() => setTagsDialogOpen(true)}>
            <Tag className="w-4 h-4 mr-2" />
            Manage Tags
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <ManageTagsDialog
        open={tagsDialogOpen}
        onOpenChange={setTagsDialogOpen}
        symbol={symbol}
      />
    </>
  )
}

function StockRow({ stock }: { stock: WatchlistStockData }) {
  const { selectedSymbols, toggleSelect, tags, groups } = useSyncWatchlist()
  const isSelected = selectedSymbols.includes(stock.symbol)
  const symbolTags = tags[stock.symbol] || []

  // Find which groups this stock belongs to
  const stockGroups = useMemo(() => {
    return Object.entries(groups)
      .filter(([_, symbols]) => symbols.includes(stock.symbol))
      .map(([name]) => name)
  }, [groups, stock.symbol])

  if (stock.isLoading) {
    return <StockRowSkeleton />
  }

  return (
    <div className="flex items-center gap-4 py-3 border-b last:border-b-0">
      {/* Checkbox */}
      <input
        type="checkbox"
        checked={isSelected}
        onChange={() => toggleSelect(stock.symbol)}
        className="h-4 w-4 rounded border-gray-300"
      />

      {/* Symbol */}
      <Link
        href={`/analysis/${stock.symbol}`}
        className="font-medium text-text-primary hover:text-primary transition-colors min-w-[60px]"
      >
        {stock.symbol}
      </Link>

      {/* Tags */}
      <div className="flex items-center gap-1 flex-wrap min-w-[100px]">
        {stockGroups.map((groupName) => (
          <Badge
            key={`group-${groupName}`}
            variant="outline"
            className="text-[10px] px-1.5 py-0"
          >
            <FolderOpen className="w-2.5 h-2.5 mr-0.5" />
            {groupName}
          </Badge>
        ))}
        {symbolTags.map((tag) => (
          <Badge
            key={`tag-${tag}`}
            variant="secondary"
            className="text-[10px] px-1.5 py-0"
          >
            {tag}
          </Badge>
        ))}
      </div>

      <div className="flex-1" />

      {/* Price */}
      <div className="text-right min-w-[80px]">
        {stock.price !== undefined ? (
          <span className="font-mono text-text-primary">${stock.price.toFixed(2)}</span>
        ) : (
          <span className="text-text-tertiary">--</span>
        )}
      </div>

      {/* Change */}
      <div className="min-w-[120px]">
        <PriceChange change={stock.change} changePercent={stock.changePercent} />
      </div>

      {/* Signal */}
      <div className="min-w-[60px]">
        {stock.signal ? (
          <SignalBadge type={stock.signal.type} score={stock.signal.score} />
        ) : stock.error ? (
          <div className="flex items-center gap-1 text-error" title={stock.error}>
            <AlertCircle className="w-4 h-4" />
            <span className="text-xs">Error</span>
          </div>
        ) : (
          <span className="text-text-tertiary text-sm">--</span>
        )}
      </div>

      {/* Actions */}
      <StockRowActions symbol={stock.symbol} />
    </div>
  )
}

export const WatchlistTable = memo(function WatchlistTable({
  stocks,
  loading = false,
  onAddClick,
  onCompareClick,
  onRefresh,
  className,
}: WatchlistTableProps) {
  const { selectedSymbols, selectAll, deselectAll, removeSelected, groups } =
    useSyncWatchlist()

  const [groupFilter, setGroupFilter] = useState<string | null>(null)
  const [manageGroupsOpen, setManageGroupsOpen] = useState(false)

  const groupNames = Object.keys(groups).sort()

  // Filter stocks by selected group
  const filteredStocks = useMemo(() => {
    if (!groupFilter) return stocks
    const groupSymbols = groups[groupFilter] || []
    return stocks.filter((stock) => groupSymbols.includes(stock.symbol))
  }, [stocks, groupFilter, groups])

  const allSelected = filteredStocks.length > 0 && selectedSymbols.length === filteredStocks.length

  if (loading && stocks.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Watchlist</span>
            <div className="h-8 w-24 bg-muted animate-pulse rounded" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <StockRowSkeleton key={i} />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (stocks.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Watchlist</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
              <Plus className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Your watchlist is empty</h3>
            <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
              Add stocks to track their performance, signals, and technical indicators
            </p>
            {onAddClick && (
              <Button onClick={onAddClick} variant="outline">
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Stock
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span>Watchlist</span>
              <span className="text-sm font-normal text-text-tertiary">
                ({filteredStocks.length} {filteredStocks.length === 1 ? 'stock' : 'stocks'})
                {groupFilter && (
                  <span className="ml-1">
                    in <span className="font-medium text-text-secondary">{groupFilter}</span>
                  </span>
                )}
              </span>
              {loading && (
                <RefreshCw className="w-4 h-4 text-text-tertiary animate-spin" />
              )}
            </div>
            <div className="flex items-center gap-2">
              {/* Refresh button */}
              {onRefresh && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onRefresh}
                  disabled={loading}
                  title="Refresh data"
                >
                  <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
                </Button>
              )}

              {/* Compare button */}
              {selectedSymbols.length > 1 && onCompareClick && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onCompareClick(selectedSymbols)}
                >
                  <BarChart3 className="w-4 h-4 mr-1" />
                  Compare ({selectedSymbols.length})
                </Button>
              )}

              {/* Select/Deselect all */}
              <Button variant="ghost" size="sm" onClick={allSelected ? deselectAll : selectAll}>
                {allSelected ? 'Deselect All' : 'Select All'}
              </Button>

              {/* Remove selected */}
              {selectedSymbols.length > 0 && (
                <Button variant="destructive" size="sm" onClick={removeSelected}>
                  <Trash2 className="w-4 h-4 mr-1" />
                  Remove ({selectedSymbols.length})
                </Button>
              )}

              {/* Add button */}
              <Button variant="outline" size="sm" onClick={onAddClick}>
                <Plus className="w-4 h-4 mr-1" />
                Add
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {/* Group Tabs */}
          {groupNames.length > 0 && (
            <Tabs
              value={groupFilter || 'all'}
              onValueChange={(v) => setGroupFilter(v === 'all' ? null : v)}
              className="mb-4"
            >
              <div className="flex items-center justify-between border-b pb-0.5 mb-4">
                <TabsList className="h-auto bg-transparent p-0 gap-6 rounded-none">
                  <TabsTrigger
                    value="all"
                    className="relative px-1 pb-2 pt-0 rounded-none border-b-2 border-transparent bg-transparent data-[state=active]:bg-transparent data-[state=active]:border-primary data-[state=active]:shadow-none text-sm font-medium"
                  >
                    All Stocks
                    <Badge variant="secondary" className="ml-2 h-5 min-w-5 px-1 font-normal bg-muted text-[10px]">
                      {stocks.length}
                    </Badge>
                  </TabsTrigger>
                  {groupNames.map((name) => (
                    <TabsTrigger
                      key={name}
                      value={name}
                      className="relative px-1 pb-2 pt-0 rounded-none border-b-2 border-transparent bg-transparent data-[state=active]:bg-transparent data-[state=active]:border-primary data-[state=active]:shadow-none text-sm font-medium"
                    >
                      {name}
                      <Badge variant="secondary" className="ml-2 h-5 min-w-5 px-1 font-normal bg-muted text-[10px]">
                        {(groups[name] || []).length}
                      </Badge>
                    </TabsTrigger>
                  ))}
                </TabsList>
                
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setManageGroupsOpen(true)}
                  className="text-text-tertiary hover:text-text-secondary h-8 px-2"
                >
                  <FolderOpen className="w-4 h-4 mr-1.5" />
                  Manage Groups
                </Button>
              </div>
            </Tabs>
          )}

          {filteredStocks.length === 0 ? (
            <div className="text-center py-8 text-text-tertiary">
              <Filter className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">
                No stocks in &ldquo;{groupFilter}&rdquo; group.
              </p>
              <Button
                variant="ghost"
                size="sm"
                className="mt-2"
                onClick={() => setGroupFilter(null)}
              >
                Show all stocks
              </Button>
            </div>
          ) : (
            <div className="divide-y">
              {filteredStocks.map((stock) => (
                <StockRow key={stock.symbol} stock={stock} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <ManageGroupsDialog
        open={manageGroupsOpen}
        onOpenChange={setManageGroupsOpen}
      />
    </>
  )
})
