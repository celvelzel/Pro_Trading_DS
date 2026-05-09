'use client'

import { memo } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight } from 'lucide-react'
import type { Trade } from '@/lib/types'

interface TradeTableProps {
  trades: Trade[]
  className?: string
}

/**
 * TradeTable - Displays backtest trade history in a Google Finance-style table.
 *
 * Shows entry/exit dates, prices, return %, and holding days.
 * Color-coded returns: green for positive, red for negative.
 */
export const TradeTable = memo(function TradeTable({
  trades,
  className,
}: TradeTableProps) {
  if (trades.length === 0) {
    return (
      <div className={cn('text-center py-8 text-text-tertiary', className)}>
        No trades executed during this backtest period
      </div>
    )
  }

  return (
    <div className={cn('overflow-x-auto', className)}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>#</TableHead>
            <TableHead>Entry Date</TableHead>
            <TableHead>Exit Date</TableHead>
            <TableHead className="text-right">Entry Price</TableHead>
            <TableHead className="text-right">Exit Price</TableHead>
            <TableHead className="text-right">Return</TableHead>
            <TableHead className="text-right">Hold Days</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((trade, index) => {
            const isPositive = trade.returnPercent >= 0
            return (
              <TableRow key={index}>
                <TableCell className="text-text-tertiary font-mono text-xs">
                  {index + 1}
                </TableCell>
                <TableCell className="font-mono text-sm">
                  {trade.entryDate}
                </TableCell>
                <TableCell className="font-mono text-sm">
                  {trade.exitDate}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  ${trade.entryPrice.toFixed(2)}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  ${trade.exitPrice.toFixed(2)}
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 font-mono text-sm font-medium',
                      isPositive ? 'text-success' : 'text-error'
                    )}
                  >
                    {isPositive ? (
                      <ArrowUpRight className="w-3 h-3" />
                    ) : (
                      <ArrowDownRight className="w-3 h-3" />
                    )}
                    {isPositive ? '+' : ''}
                    {trade.returnPercent.toFixed(2)}%
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono text-sm text-text-secondary">
                  {trade.holdingDays}d
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
})
