'use client'

import { memo, useState, useMemo } from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
  const variant =
    type === 'bullish' ? 'success' : type === 'bearish' ? 'destructive' : 'warning'

  return (
    <Badge variant={variant} className="font-mono tabular-nums">
      {score}
    </Badge>
  )
}

function PriceChange({ change, changePercent }: { change?: number; changePercent?: number }) {
  if (change === undefined || changePercent === undefined) {
    return <span className="text-sm text-muted-foreground">--</span>
  }

  const isPositive = change >= 0
  const Icon = isPositive ? TrendingUp : TrendingDown

  return (
    <div
      className={cn(
        'flex items-center justify-end gap-1 font-mono text-sm font-medium tabular-nums',
        isPositive ? 'text-success' : 'text-error'
      )}
    >
      <Icon className="size-3.5 shrink-0" />
      <span>
        {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
      </span>
    </div>
  )
}

function StockRowSkeleton() {
  return (
    <TableRow className="hover:bg-transparent">
      <TableCell className="w-10">
        <Skeleton className="size-4" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-4 w-14" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-4 w-24" />
      </TableCell>
      <TableCell>
        <Skeleton className="ml-auto h-4 w-16" />
      </TableCell>
      <TableCell>
        <Skeleton className="ml-auto h-4 w-28" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-5 w-12 rounded-full" />
      </TableCell>
      <TableCell className="w-10">
        <Skeleton className="size-4" />
      </TableCell>
    </TableRow>
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
              className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              aria-label={`Actions for ${symbol}`}
            />
          }
        >
          <MoreHorizontal className="size-4" />
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
      .filter(([, symbols]) => symbols.includes(stock.symbol))
      .map(([name]) => name)
  }, [groups, stock.symbol])

  if (stock.isLoading) {
    return <StockRowSkeleton />
  }

  return (
    <TableRow data-state={isSelected ? 'selected' : undefined}>
      {/* Checkbox */}
      <TableCell className="w-10">
        <Checkbox
          checked={isSelected}
          onChange={() => toggleSelect(stock.symbol)}
        />
      </TableCell>

      {/* Symbol */}
      <TableCell>
        <Link
          href={`/analysis/${stock.symbol}`}
          className="font-mono text-sm font-semibold text-foreground transition-colors hover:text-primary"
        >
          {stock.symbol}
        </Link>
      </TableCell>

      {/* Tags */}
      <TableCell>
        <div className="flex max-w-60 flex-wrap items-center gap-1">
          {stockGroups.map((groupName) => (
            <Badge
              key={`group-${groupName}`}
              variant="outline"
              className="px-1.5 py-0 text-[10px]"
            >
              <FolderOpen className="size-2.5" />
              {groupName}
            </Badge>
          ))}
          {symbolTags.map((tag) => (
            <Badge
              key={`tag-${tag}`}
              variant="secondary"
              className="px-1.5 py-0 text-[10px]"
            >
              {tag}
            </Badge>
          ))}
        </div>
      </TableCell>

      {/* Price */}
      <TableCell className="text-right">
        {stock.price !== undefined ? (
          <span className="font-mono text-sm font-medium tabular-nums text-foreground">
            ${stock.price.toFixed(2)}
          </span>
        ) : (
          <span className="text-sm text-muted-foreground">--</span>
        )}
      </TableCell>

      {/* Change */}
      <TableCell className="text-right">
        <PriceChange change={stock.change} changePercent={stock.changePercent} />
      </TableCell>

      {/* Signal */}
      <TableCell>
        {stock.signal ? (
          <SignalBadge type={stock.signal.type} score={stock.signal.score} />
        ) : stock.error ? (
          <div className="flex items-center gap-1 text-error" title={stock.error}>
            <AlertCircle className="size-4" />
            <span className="text-xs">Error</span>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">--</span>
        )}
      </TableCell>

      {/* Actions */}
      <TableCell className="w-10">
        <StockRowActions symbol={stock.symbol} />
      </TableCell>
    </TableRow>
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
          <CardTitle className="flex w-full items-center justify-between">
            <span>Watchlist</span>
            <Skeleton className="h-8 w-24" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableBody>
              {[1, 2, 3].map((i) => (
                <StockRowSkeleton key={i} />
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    )
  }

  if (stocks.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Watchlist</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="py-12 text-center">
            <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-full bg-muted">
              <Plus className="size-8 text-muted-foreground" />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-foreground">Your watchlist is empty</h3>
            <p className="mx-auto mb-6 max-w-sm text-sm text-muted-foreground">
              Add stocks to track their performance, signals, and technical indicators
            </p>
            {onAddClick && (
              <Button onClick={onAddClick} variant="outline">
                <Plus />
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
          <CardTitle className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>Watchlist</span>
            <span className="text-sm font-normal text-muted-foreground">
              ({filteredStocks.length} {filteredStocks.length === 1 ? 'stock' : 'stocks'})
              {groupFilter && (
                <span className="ml-1">
                  in <span className="font-medium text-foreground">{groupFilter}</span>
                </span>
              )}
            </span>
            {loading && (
              <RefreshCw className="size-4 animate-spin text-muted-foreground" />
            )}
          </CardTitle>
          <CardAction>
            <div className="flex flex-wrap items-center gap-2">
              {/* Refresh button */}
              {onRefresh && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={onRefresh}
                  disabled={loading}
                  title="Refresh data"
                >
                  <RefreshCw className={cn(loading && 'animate-spin')} />
                </Button>
              )}

              {/* Compare button */}
              {selectedSymbols.length > 1 && onCompareClick && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onCompareClick(selectedSymbols)}
                >
                  <BarChart3 />
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
                  <Trash2 />
                  Remove ({selectedSymbols.length})
                </Button>
              )}

              {/* Add button */}
              <Button size="sm" onClick={onAddClick}>
                <Plus />
                Add
              </Button>
            </div>
          </CardAction>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Group Tabs */}
          {groupNames.length > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b pb-1">
              <Tabs
                value={groupFilter || 'all'}
                onValueChange={(v) => setGroupFilter(v === 'all' ? null : v)}
              >
                <TabsList variant="line" className="h-auto flex-wrap justify-start">
                  <TabsTrigger value="all" className="px-1.5 text-sm">
                    All Stocks
                    <Badge
                      variant="secondary"
                      className="ml-1.5 h-5 min-w-5 px-1 font-mono text-[10px] tabular-nums"
                    >
                      {stocks.length}
                    </Badge>
                  </TabsTrigger>
                  {groupNames.map((name) => (
                    <TabsTrigger key={name} value={name} className="px-1.5 text-sm">
                      {name}
                      <Badge
                        variant="secondary"
                        className="ml-1.5 h-5 min-w-5 px-1 font-mono text-[10px] tabular-nums"
                      >
                        {(groups[name] || []).length}
                      </Badge>
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => setManageGroupsOpen(true)}
                className="text-muted-foreground hover:text-foreground"
              >
                <FolderOpen />
                Manage Groups
              </Button>
            </div>
          )}

          {filteredStocks.length === 0 ? (
            <div className="py-10 text-center text-muted-foreground">
              <Filter className="mx-auto mb-2 size-8 opacity-50" />
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
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-10" />
                  <TableHead className="text-xs text-muted-foreground">Symbol</TableHead>
                  <TableHead className="text-xs text-muted-foreground">Tags</TableHead>
                  <TableHead className="text-right text-xs text-muted-foreground">Price</TableHead>
                  <TableHead className="text-right text-xs text-muted-foreground">Change</TableHead>
                  <TableHead className="text-xs text-muted-foreground">Signal</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredStocks.map((stock) => (
                  <StockRow key={stock.symbol} stock={stock} />
                ))}
              </TableBody>
            </Table>
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
