'use client';

import { useState } from 'react';
import { BacktestForm, BacktestParams, MetricsCard } from '@/components/backtest';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BacktestMetrics } from '@/stores/strategyStore';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

interface Trade {
  entryDate: string;
  exitDate?: string;
  entryPrice: number;
  exitPrice?: number;
  returnPercent: number;
  holdingDays: number;
}

interface BacktestResult {
  strategy_id: string;
  strategy_name: string;
  symbol?: string;
  symbols?: string[];
  metrics: BacktestMetrics | null;
  trades: Trade[];
  equityCurve: number[];
}

export default function BacktestPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunBacktest = async (params: BacktestParams) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let response;

      if (params.mode === 'single') {
        const queryParams = new URLSearchParams({
          strategy_id: params.strategyId,
          symbol: params.symbol || '',
        });
        if (params.startDate) queryParams.append('start_date', params.startDate);
        if (params.endDate) queryParams.append('end_date', params.endDate);

        response = await fetch(`${API_BASE}/backtest/backtest/strategy?${queryParams}`, {
          method: 'POST',
        });
      } else {
        response = await fetch(`${API_BASE}/backtest/backtest/portfolio`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbols: params.symbols,
            strategy_id: params.strategyId,
            start_date: params.startDate,
            end_date: params.endDate,
          }),
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Backtest failed');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Strategy Backtest</h1>
        <p className="text-muted-foreground mt-2">
          Test your strategies against historical data
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Backtest Form */}
        <div className="lg:col-span-1">
          <BacktestForm onRun={handleRunBacktest} loading={loading} />
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-2 space-y-6">
          {error && (
            <Card className="border-destructive">
              <CardContent className="pt-6">
                <p className="text-destructive">{error}</p>
              </CardContent>
            </Card>
          )}

          {loading && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  <span className="ml-3">Running backtest...</span>
                </div>
              </CardContent>
            </Card>
          )}

          {result && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>
                    {result.strategy_name}
                    {result.symbol && ` - ${result.symbol}`}
                    {result.symbols && ` - ${result.symbols.join(', ')}`}
                  </CardTitle>
                </CardHeader>
              </Card>

              {result.metrics && (
                <MetricsCard metrics={result.metrics} />
              )}

              {result.trades.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Trades ({result.trades.length})</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2">Entry Date</th>
                            <th className="text-left py-2">Exit Date</th>
                            <th className="text-right py-2">Entry Price</th>
                            <th className="text-right py-2">Exit Price</th>
                            <th className="text-right py-2">Return</th>
                            <th className="text-right py-2">Days</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.trades.map((trade, i) => (
                            <tr key={i} className="border-b">
                              <td className="py-2">{trade.entryDate}</td>
                              <td className="py-2">{trade.exitDate || '-'}</td>
                              <td className="text-right py-2">${trade.entryPrice?.toFixed(2)}</td>
                              <td className="text-right py-2">${trade.exitPrice?.toFixed(2) || '-'}</td>
                              <td className={`text-right py-2 ${trade.returnPercent > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {trade.returnPercent?.toFixed(2)}%
                              </td>
                              <td className="text-right py-2">{trade.holdingDays}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}

              {result.equityCurve.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Equity Curve</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                      Chart placeholder - integrate with your charting library
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {!loading && !result && !error && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <p className="text-lg mb-2">No backtest results yet</p>
                  <p className="text-sm">Select a strategy and run a backtest to see results</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
