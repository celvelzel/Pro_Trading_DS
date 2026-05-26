'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

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

export function TradeList({ trades }: TradeListProps) {
  const openTrades = trades.filter(t => t.status === 'open');
  const closedTrades = trades.filter(t => t.status === 'closed');

  const renderTradeRow = (trade: Trade) => (
    <tr key={trade.id} className="border-b">
      <td className="py-2 font-medium">{trade.symbol}</td>
      <td className="py-2">{trade.entryDate}</td>
      <td className="text-right py-2">${trade.entryPrice.toFixed(2)}</td>
      <td className="text-right py-2">{trade.shares}</td>
      {trade.status === 'closed' && (
        <>
          <td className="py-2">{trade.exitDate || '-'}</td>
          <td className="text-right py-2">${trade.exitPrice?.toFixed(2) || '-'}</td>
          <td className={`text-right py-2 font-medium ${
            (trade.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            ${trade.pnl?.toFixed(2) || '-'}
          </td>
          <td className={`text-right py-2 font-medium ${
            (trade.pnlPercent || 0) >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
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
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2">Symbol</th>
                      <th className="text-left py-2">Entry Date</th>
                      <th className="text-right py-2">Entry Price</th>
                      <th className="text-right py-2">Shares</th>
                    </tr>
                  </thead>
                  <tbody>
                    {openTrades.map(renderTradeRow)}
                  </tbody>
                </table>
              </div>
            )}
          </TabsContent>
          
          <TabsContent value="closed">
            {closedTrades.length === 0 ? (
              <p className="text-muted-foreground py-4">No closed trades</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2">Symbol</th>
                      <th className="text-left py-2">Entry Date</th>
                      <th className="text-right py-2">Entry Price</th>
                      <th className="text-right py-2">Shares</th>
                      <th className="text-left py-2">Exit Date</th>
                      <th className="text-right py-2">Exit Price</th>
                      <th className="text-right py-2">P&L</th>
                      <th className="text-right py-2">Return</th>
                    </tr>
                  </thead>
                  <tbody>
                    {closedTrades.map(renderTradeRow)}
                  </tbody>
                </table>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
