'use client'

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
    <span className={isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
      {isPositive ? '+' : ''}{formatCurrency(value)}
      <span className="text-xs ml-1">({formatPercent(percent)})</span>
    </span>
  )
}

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
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">Failed to load portfolio: {(error as Error).message}</p>
            <Button variant="outline" onClick={() => refetch()} className="mt-4">
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Portfolio</h1>
          <p className="text-text-secondary mt-1">
            Track your positions and monitor P&L in real-time
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh
          </Button>
          <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="w-4 h-4 mr-1" />
                Add Position
              </Button>
            </DialogTrigger>
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
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Equity */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">Total Equity</CardTitle>
            <PieChart className="h-4 w-4 text-text-tertiary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(totalEquity)}</div>
            <p className="text-xs text-text-tertiary mt-1">
              {positionCount} position{positionCount !== 1 ? 's' : ''} + cash
            </p>
          </CardContent>
        </Card>

        {/* Total P&L */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">Total P&L</CardTitle>
            {totalPnl >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-500" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {totalPnl >= 0 ? '+' : ''}{formatCurrency(totalPnl)}
            </div>
            <p className={`text-xs mt-1 ${totalPnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {formatPercent(totalPnlPercent)}
            </p>
          </CardContent>
        </Card>

        {/* Market Value */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">Market Value</CardTitle>
            <BarChart3 className="h-4 w-4 text-text-tertiary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(totalMarketValue)}</div>
            <p className="text-xs text-text-tertiary mt-1">
              Cost: {formatCurrency(totalCost)}
            </p>
          </CardContent>
        </Card>

        {/* Cash Balance */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">Cash Balance</CardTitle>
            <Wallet className="h-4 w-4 text-text-tertiary" />
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
                <div className="text-2xl font-bold">{formatCurrency(cash)}</div>
                <button
                  onClick={() => {
                    setCashInput(cash.toString())
                    setEditingCash(true)
                  }}
                  className="text-xs text-primary hover:underline mt-1"
                >
                  Edit cash balance
                </button>
              </>
            )}
          </CardContent>
        </Card>
      </div>

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
            <div className="text-center py-12 text-text-tertiary">
              <DollarSign className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">No positions yet</p>
              <p className="text-sm mt-1">Click &quot;Add Position&quot; to start tracking your portfolio</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead className="text-right">Shares</TableHead>
                    <TableHead className="text-right">Cost Basis</TableHead>
                    <TableHead className="text-right">Current Price</TableHead>
                    <TableHead className="text-right">Market Value</TableHead>
                    <TableHead className="text-right">P&L</TableHead>
                    <TableHead>Strategy</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {positions.map((pos) => (
                    <TableRow key={pos.id}>
                      <TableCell className="font-medium">{pos.symbol}</TableCell>
                      <TableCell className="text-right">{pos.shares.toLocaleString()}</TableCell>
                      <TableCell className="text-right">{formatCurrency(pos.cost_basis)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(pos.current_price)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(pos.market_value)}</TableCell>
                      <TableCell className="text-right">
                        <PnlCell value={pos.pnl} percent={pos.pnl_percent} />
                      </TableCell>
                      <TableCell className="text-text-tertiary text-sm">
                        {pos.strategy_id || '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deletePosition(pos.id)}
                          className="h-8 w-8 p-0 text-destructive hover:text-destructive"
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
                  <TableRow>
                    <TableHead>Strategy</TableHead>
                    <TableHead className="text-right">Positions</TableHead>
                    <TableHead className="text-right">Cost</TableHead>
                    <TableHead className="text-right">Market Value</TableHead>
                    <TableHead className="text-right">P&L</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pnlData.strategies.map((strategy) => (
                    <TableRow key={strategy.strategy_id}>
                      <TableCell className="font-medium">{strategy.strategy_id}</TableCell>
                      <TableCell className="text-right">{strategy.position_count}</TableCell>
                      <TableCell className="text-right">{formatCurrency(strategy.total_cost)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(strategy.total_market_value)}</TableCell>
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
