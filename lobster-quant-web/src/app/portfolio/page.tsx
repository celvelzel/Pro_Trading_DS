'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { PageHeader } from '@/components/layout/PageHeader'
import { cn } from '@/lib/utils'
import { useSyncPortfolio } from '@/stores/portfolioStore'
import { usePortfolioPnl } from '@/hooks/usePortfolio'
import {
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Wallet,
  PieChart,
  BarChart3,
} from 'lucide-react'

// ============================================================================
// Helpers
// ============================================================================

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function PnlCell({ value, percent }: { value: number; percent: number }) {
  const isPositive = value >= 0
  return (
    <span className={cn('font-mono tabular-nums', isPositive ? 'text-success' : 'text-error')}>
      {isPositive ? '+' : ''}{formatCurrency(value)}
      <span className="ml-1 text-xs">({formatPercent(percent)})</span>
    </span>
  )
}

const headCellClass = 'text-xs font-medium uppercase tracking-wide text-muted-foreground'
const numCellClass = 'font-mono tabular-nums'

// ============================================================================
// Page Component
// ============================================================================

export default function PortfolioPage() {
  const {
    positions,
    cash,
    totalEquity,
    totalPnl,
    totalPnlPercent,
    totalCost,
    totalMarketValue,
    positionCount,
    isLoading,
    error,
    addPosition,
    deletePosition,
    setCash,
    refetch,
    isAdding,
  } = useSyncPortfolio()

  const { data: pnlData } = usePortfolioPnl()

  // Add position form state
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [formSymbol, setFormSymbol] = useState('')
  const [formShares, setFormShares] = useState('')
  const [formCostBasis, setFormCostBasis] = useState('')
  const [formStrategyId, setFormStrategyId] = useState('')

  // Cash edit state
  const [editingCash, setEditingCash] = useState(false)
  const [cashInput, setCashInput] = useState('')

  const handleAddPosition = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formSymbol.trim() || !formShares || !formCostBasis) return

    addPosition({
      symbol: formSymbol.trim().toUpperCase(),
      shares: parseInt(formShares, 10),
      cost_basis: parseFloat(formCostBasis),
      strategy_id: formStrategyId.trim() || undefined,
    })

    setFormSymbol('')
    setFormShares('')
    setFormCostBasis('')
    setFormStrategyId('')
    setAddDialogOpen(false)
  }

  const handleSetCash = () => {
    const value = parseFloat(cashInput)
    if (!isNaN(value) && value >= 0) {
      setCash(value)
      setEditingCash(false)
      setCashInput('')
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center p-6">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto w-full max-w-[1600px] p-4 md:p-6">
        <Card className="border-error/50">
          <CardContent className="pt-6">
            <p className="text-error">Failed to load portfolio: {(error as Error).message}</p>
            <Button variant="outline" onClick={() => refetch()} className="mt-4">
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const positionAllocation = totalEquity > 0 ? (totalMarketValue / totalEquity) * 100 : 0
  const cashAllocation = totalEquity > 0 ? (cash / totalEquity) * 100 : 0

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
      {/* Page Header */}
      <PageHeader
        title="Portfolio"
        description="Track your positions and monitor P&L in real-time"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-1" />
              Refresh
            </Button>
            <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
              <DialogTrigger
                render={
                  <Button size="sm">
                    <Plus className="w-4 h-4 mr-1" />
                    Add Position
                  </Button>
                }
              />
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Position</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleAddPosition} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="symbol">Symbol</Label>
                    <Input
                      id="symbol"
                      placeholder="AAPL"
                      value={formSymbol}
                      onChange={(e) => setFormSymbol(e.target.value.toUpperCase())}
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="shares">Shares</Label>
                      <Input
                        id="shares"
                        type="number"
                        min="1"
                        placeholder="100"
                        value={formShares}
                        onChange={(e) => setFormShares(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="costBasis">Cost Basis ($)</Label>
                      <Input
                        id="costBasis"
                        type="number"
                        min="0.01"
                        step="0.01"
                        placeholder="150.00"
                        value={formCostBasis}
                        onChange={(e) => setFormCostBasis(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="strategyId">Strategy ID (optional)</Label>
                    <Input
                      id="strategyId"
                      placeholder="momentum-v1"
                      value={formStrategyId}
                      onChange={(e) => setFormStrategyId(e.target.value)}
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={isAdding}>
                    {isAdding ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Plus className="w-4 h-4 mr-2" />
                    )}
                    Add Position
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </>
        }
      />

      <nav className="flex gap-4 text-sm" aria-label="只读合成金融演示">
        <Link
          href="/copilot?workflow=portfolio"
          className="text-muted-foreground transition-colors hover:text-foreground"
        >
          Portfolio 合成只读演示
        </Link>
        <Link
          href="/copilot?workflow=combined"
          className="text-muted-foreground transition-colors hover:text-foreground"
        >
          Combined 合成只读演示
        </Link>
      </nav>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Total Equity */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
            <CardTitle className="text-[13px] font-medium text-muted-foreground">Total Equity</CardTitle>
            <PieChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="font-mono text-2xl font-semibold tracking-tight tabular-nums">{formatCurrency(totalEquity)}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              {positionCount} position{positionCount !== 1 ? 's' : ''} + cash
            </p>
          </CardContent>
        </Card>

        {/* Total P&L */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
            <CardTitle className="text-[13px] font-medium text-muted-foreground">Total P&L</CardTitle>
            {totalPnl >= 0 ? (
              <TrendingUp className="h-4 w-4 text-success" />
            ) : (
              <TrendingDown className="h-4 w-4 text-error" />
            )}
          </CardHeader>
          <CardContent>
            <div className={cn(
              'font-mono text-2xl font-semibold tracking-tight tabular-nums',
              totalPnl >= 0 ? 'text-success' : 'text-error'
            )}>
              {totalPnl >= 0 ? '+' : ''}{formatCurrency(totalPnl)}
            </div>
            <p className={cn(
              'mt-1 font-mono text-xs tabular-nums',
              totalPnl >= 0 ? 'text-success' : 'text-error'
            )}>
              {formatPercent(totalPnlPercent)}
            </p>
          </CardContent>
        </Card>

        {/* Market Value */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
            <CardTitle className="text-[13px] font-medium text-muted-foreground">Market Value</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="font-mono text-2xl font-semibold tracking-tight tabular-nums">{formatCurrency(totalMarketValue)}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              Cost: <span className="font-mono tabular-nums">{formatCurrency(totalCost)}</span>
            </p>
          </CardContent>
        </Card>

        {/* Cash Balance */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
            <CardTitle className="text-[13px] font-medium text-muted-foreground">Cash Balance</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {editingCash ? (
              <div className="flex gap-2">
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={cashInput}
                  onChange={(e) => setCashInput(e.target.value)}
                  placeholder={cash.toString()}
                  className="h-8"
                  autoFocus
                />
                <Button size="sm" onClick={handleSetCash} className="h-8 px-2">
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setEditingCash(false)}
                  className="h-8 px-2"
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <>
                <div className="font-mono text-2xl font-semibold tracking-tight tabular-nums">{formatCurrency(cash)}</div>
                <button
                  onClick={() => {
                    setCashInput(cash.toString())
                    setEditingCash(true)
                  }}
                  className="mt-1 text-xs text-primary hover:underline"
                >
                  Edit cash balance
                </button>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Asset Allocation */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChart className="h-4 w-4 text-muted-foreground" />
            Asset Allocation
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full bg-chart-1" style={{ width: `${positionAllocation}%` }} />
            <div className="h-full bg-chart-3" style={{ width: `${cashAllocation}%` }} />
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-chart-1" />
              <span className="text-muted-foreground">Positions</span>
              <span className="font-mono font-medium tabular-nums">{formatCurrency(totalMarketValue)}</span>
              <span className="font-mono text-xs text-muted-foreground tabular-nums">{positionAllocation.toFixed(1)}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-chart-3" />
              <span className="text-muted-foreground">Cash</span>
              <span className="font-mono font-medium tabular-nums">{formatCurrency(cash)}</span>
              <span className="font-mono text-xs text-muted-foreground tabular-nums">{cashAllocation.toFixed(1)}%</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Positions Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="w-5 h-5" />
            Positions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {positions.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <DollarSign className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">No positions yet</p>
              <p className="mt-1 text-sm">Click &quot;Add Position&quot; to start tracking your portfolio</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className={headCellClass}>Symbol</TableHead>
                    <TableHead className={cn(headCellClass, 'text-right')}>Shares</TableHead>
                    <TableHead className={cn(headCellClass, 'text-right')}>Cost Basis</TableHead>
                    <TableHead className={cn(headCellClass, 'text-right')}>Current Price</TableHead>
                    <TableHead className={cn(headCellClass, 'text-right')}>Market Value</TableHead>
                    <TableHead className={cn(headCellClass, 'text-right')}>P&L</TableHead>
                    <TableHead className={headCellClass}>Strategy</TableHead>
                    <TableHead className={cn(headCellClass, 'text-right')}>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {positions.map((pos) => (
                    <TableRow key={pos.id}>
                      <TableCell className="font-mono font-medium">{pos.symbol}</TableCell>
                      <TableCell className={cn(numCellClass, 'text-right')}>{pos.shares.toLocaleString()}</TableCell>
                      <TableCell className={cn(numCellClass, 'text-right')}>{formatCurrency(pos.cost_basis)}</TableCell>
                      <TableCell className={cn(numCellClass, 'text-right')}>{formatCurrency(pos.current_price)}</TableCell>
                      <TableCell className={cn(numCellClass, 'text-right')}>{formatCurrency(pos.market_value)}</TableCell>
                      <TableCell className="text-right">
                        <PnlCell value={pos.pnl} percent={pos.pnl_percent} />
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {pos.strategy_id || '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deletePosition(pos.id)}
                          className="h-8 w-8 p-0 text-error hover:text-error"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* P&L by Strategy */}
      {pnlData && pnlData.strategies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              P&L by Strategy
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className={headCellClass}>Strategy</TableHead>
                    <TableHead className={cn(headCellClass, 'text-right')}>Positions</TableHead>
                    <TableHead className={cn(headCellClass, 'text-right')}>Cost</TableHead>
                    <TableHead className={cn(headCellClass, 'text-right')}>Market Value</TableHead>
                    <TableHead className={cn(headCellClass, 'text-right')}>P&L</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pnlData.strategies.map((strategy) => (
                    <TableRow key={strategy.strategy_id}>
                      <TableCell className="font-mono font-medium">{strategy.strategy_id}</TableCell>
                      <TableCell className={cn(numCellClass, 'text-right')}>{strategy.position_count}</TableCell>
                      <TableCell className={cn(numCellClass, 'text-right')}>{formatCurrency(strategy.total_cost)}</TableCell>
                      <TableCell className={cn(numCellClass, 'text-right')}>{formatCurrency(strategy.total_market_value)}</TableCell>
                      <TableCell className="text-right">
                        <PnlCell value={strategy.pnl} percent={strategy.pnl_percent} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
