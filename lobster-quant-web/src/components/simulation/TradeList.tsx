'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { cn } from '@/lib/utils';

interface Trade {
  id: string;
  symbol: string;
  entryDate: string;
  entryPrice: number;
  exitDate?: string;
  exitPrice?: number;
  shares: number;
  status: 'open' | 'closed';
  pnl?: number;
  pnlPercent?: number;
}

interface TradeListProps {
  trades: Trade[];
}

const headerCellClass = 'py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground';
const numCellClass = 'py-2.5 text-right font-mono tabular-nums';

export function TradeList({ trades }: TradeListProps) {
  const openTrades = trades.filter(t => t.status === 'open');
  const closedTrades = trades.filter(t => t.status === 'closed');

  const renderTradeCard = (trade: Trade) => (
    <Card key={trade.id} className="mb-4 md:hidden">
      <CardContent className="space-y-3 p-4">
        <div className="flex justify-between items-center">
          <span className="font-mono text-lg font-semibold text-foreground">{trade.symbol}</span>
          <Badge variant={trade.status === 'open' ? 'default' : 'secondary'}>
            {trade.status.toUpperCase()}
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Entry Date</p>
            <p className="font-mono font-medium tabular-nums">{trade.entryDate}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Entry Price</p>
            <p className="font-mono font-medium tabular-nums">${trade.entryPrice.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Shares</p>
            <p className="font-mono font-medium tabular-nums">{trade.shares}</p>
          </div>
          {trade.status === 'closed' && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Exit Price</p>
              <p className="font-mono font-medium tabular-nums">${trade.exitPrice?.toFixed(2) || '-'}</p>
            </div>
          )}
        </div>

        {trade.status === 'closed' && (
          <div className="flex justify-between items-center border-t border-border pt-2">
            <div className="flex gap-4">
              <div>
                <p className="text-xs text-muted-foreground">P&L</p>
                <p className={cn(
                  "font-mono font-bold tabular-nums",
                  (trade.pnl || 0) >= 0 ? "text-success" : "text-error"
                )}>
                  ${trade.pnl?.toFixed(2) || '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Return</p>
                <p className={cn(
                  "font-mono font-bold tabular-nums",
                  (trade.pnlPercent || 0) >= 0 ? "text-success" : "text-error"
                )}>
                  {trade.pnlPercent?.toFixed(2) || '-'}%
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Exit Date</p>
              <p className="font-mono text-sm font-medium tabular-nums">{trade.exitDate || '-'}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );

  const renderTradeRow = (trade: Trade) => (
    <tr key={trade.id} className="border-b border-border transition-colors hover:bg-muted/50">
      <td className="py-2.5 font-mono font-medium">{trade.symbol}</td>
      <td className="py-2.5 font-mono text-muted-foreground tabular-nums">{trade.entryDate}</td>
      <td className={numCellClass}>${trade.entryPrice.toFixed(2)}</td>
      <td className={numCellClass}>{trade.shares}</td>
      {trade.status === 'closed' && (
        <>
          <td className="py-2.5 font-mono text-muted-foreground tabular-nums">{trade.exitDate || '-'}</td>
          <td className={numCellClass}>${trade.exitPrice?.toFixed(2) || '-'}</td>
          <td className={cn(numCellClass, 'font-medium',
            (trade.pnl || 0) >= 0 ? 'text-success' : 'text-error'
          )}>
            ${trade.pnl?.toFixed(2) || '-'}
          </td>
          <td className={cn(numCellClass, 'font-medium',
            (trade.pnlPercent || 0) >= 0 ? 'text-success' : 'text-error'
          )}>
            {trade.pnlPercent?.toFixed(2) || '-'}%
          </td>
        </>
      )}
    </tr>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Trades
          <Badge variant="outline">{trades.length} total</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="open">
          <TabsList>
            <TabsTrigger value="open">
              Open ({openTrades.length})
            </TabsTrigger>
            <TabsTrigger value="closed">
              Closed ({closedTrades.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="open">
            {openTrades.length === 0 ? (
              <p className="text-muted-foreground py-4">No open trades</p>
            ) : (
              <>
                <div className="md:hidden">
                  {openTrades.map(renderTradeCard)}
                </div>
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className={`text-left ${headerCellClass}`}>Symbol</th>
                        <th className={`text-left ${headerCellClass}`}>Entry Date</th>
                        <th className={`text-right ${headerCellClass}`}>Entry Price</th>
                        <th className={`text-right ${headerCellClass}`}>Shares</th>
                      </tr>
                    </thead>
                    <tbody>
                      {openTrades.map(renderTradeRow)}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </TabsContent>

          <TabsContent value="closed">
            {closedTrades.length === 0 ? (
              <p className="text-muted-foreground py-4">No closed trades</p>
            ) : (
              <>
                <div className="md:hidden">
                  {closedTrades.map(renderTradeCard)}
                </div>
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className={`text-left ${headerCellClass}`}>Symbol</th>
                        <th className={`text-left ${headerCellClass}`}>Entry Date</th>
                        <th className={`text-right ${headerCellClass}`}>Entry Price</th>
                        <th className={`text-right ${headerCellClass}`}>Shares</th>
                        <th className={`text-left ${headerCellClass}`}>Exit Date</th>
                        <th className={`text-right ${headerCellClass}`}>Exit Price</th>
                        <th className={`text-right ${headerCellClass}`}>P&L</th>
                        <th className={`text-right ${headerCellClass}`}>P&L %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {closedTrades.map(renderTradeRow)}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
