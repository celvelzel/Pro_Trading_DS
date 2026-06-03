'use client';

import { useState, useCallback } from 'react';
import { BacktestForm, BacktestParams, MetricsCard } from '@/components/backtest';
import { BacktestHistory } from '@/components/backtest/BacktestHistory';
import { BacktestComparison } from '@/components/backtest/BacktestComparison';
import { ParameterSweep } from '@/components/backtest/ParameterSweep';
import { WalkForward } from '@/components/backtest/WalkForward';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { HelpTooltip } from '@/components/ui/help-tooltip';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import { Button } from '@/components/ui/button';
import { useRunBacktest, type BacktestHistoryEntry, type BacktestPageResult } from '@/hooks/useBacktest';
import { showToastError } from '@/hooks/useApiQuery';
import { History, GitCompare, SlidersHorizontal, Play, TrendingUp } from 'lucide-react';
import { ExportButton } from '@/components/ui/export-button';

// ============================================================================
// localStorage Helpers for Backtest History
// ============================================================================

const STORAGE_KEY = 'backtest_history';

function loadLocalHistory(): BacktestHistoryEntry[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveLocalHistory(entries: BacktestHistoryEntry[]): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // localStorage full or unavailable — silently ignore
  }
}

function resultToHistoryEntry(result: BacktestPageResult): BacktestHistoryEntry {
  return {
    id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date().toISOString(),
    symbol: result.symbol ?? (result.symbols?.join(', ') ?? ''),
    strategyId: result.strategy_id,
    strategyName: result.strategy_name,
    params: {},
    metrics: (result.metrics ?? {}) as Record<string, unknown>,
    trades: result.trades as unknown as Record<string, unknown>[],
    equityCurve: (result.equityCurve ?? []) as unknown as Record<string, unknown>[],
  };
}

// ============================================================================
// Skeleton Loading Component
// ============================================================================

function BacktestResultSkeleton() {
  return (
    <div className="space-y-6">
      {/* Strategy name skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
      </Card>

      {/* Metrics skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-7 w-20" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Trades table skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-36" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {/* Header row */}
            <div className="grid grid-cols-6 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
            {/* Data rows */}
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="grid grid-cols-6 gap-4">
                {Array.from({ length: 6 }).map((_, j) => (
                  <Skeleton key={j} className="h-4 w-full" />
                ))}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Equity curve skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// Backtest Page
// ============================================================================

export default function BacktestPage() {
  const runBacktest = useRunBacktest();
  const [activeTab, setActiveTab] = useState('new');
  const [compareEntries, setCompareEntries] = useState<BacktestHistoryEntry[]>([]);
  const [localHistory, setLocalHistory] = useState<BacktestHistoryEntry[]>(() => loadLocalHistory());

  const handleRunBacktest = async (params: BacktestParams) => {
    try {
      const result = await runBacktest.mutateAsync(params);
      // Persist to local history after successful backtest
      const entry = resultToHistoryEntry(result);
      setLocalHistory((prev) => {
        const next = [entry, ...prev].slice(0, 50); // keep max 50 entries
        saveLocalHistory(next);
        return next;
      });
    } catch (err) {
      showToastError(err);
    }
  };

  const handleCompare = useCallback((entries: BacktestHistoryEntry[]) => {
    setCompareEntries(entries);
    setActiveTab('comparison');
  }, []);

  const handleBackFromComparison = useCallback(() => {
    setCompareEntries([]);
    setActiveTab('history');
  }, []);

  const result = runBacktest.data ?? null;
  const loading = runBacktest.isPending;
  const error = runBacktest.error?.message ?? null;

  return (
    <div className="container mx-auto py-8">
      <div className="mb-8">
        <div className="flex items-center gap-2">
          <h1 className="text-3xl font-bold">Strategy Backtest</h1>
          <HelpTooltip helpKey="backtest.title" />
        </div>
        <p className="text-muted-foreground mt-2">
          Test your strategies against historical data
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="line" className="mb-6">
          <TabsTrigger value="new">
            <Play className="h-4 w-4 mr-1.5" />
            New Backtest
          </TabsTrigger>
          <TabsTrigger value="history">
            <History className="h-4 w-4 mr-1.5" />
            History
          </TabsTrigger>
          <TabsTrigger value="comparison">
            <GitCompare className="h-4 w-4 mr-1.5" />
            Comparison
          </TabsTrigger>
          <TabsTrigger value="sweep">
            <SlidersHorizontal className="h-4 w-4 mr-1.5" />
            Parameter Sweep
          </TabsTrigger>
          <TabsTrigger value="walkforward">
            <TrendingUp className="h-4 w-4 mr-1.5" />
            Walk-Forward
          </TabsTrigger>
        </TabsList>

        {/* ================================================================ */}
        {/* New Backtest Tab */}
        {/* ================================================================ */}
        <TabsContent value="new">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left: Backtest Form */}
            <div className="lg:col-span-1">
              <BacktestForm onRun={handleRunBacktest} loading={loading} />
            </div>

            {/* Right: Results */}
            <div className="lg:col-span-2 space-y-6">
              {error && (
                <ErrorState
                  message={error}
                  onRetry={runBacktest.variables ? () => handleRunBacktest(runBacktest.variables!) : undefined}
                />
              )}

              {loading && <BacktestResultSkeleton />}

              {result && !loading && (
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
                        <div className="flex items-center justify-between">
                          <CardTitle>Trades ({result.trades.length})</CardTitle>
                          <ExportButton
                            data={result.trades}
                            columns={[
                              { key: 'entryDate', header: 'Entry Date' },
                              { key: 'exitDate', header: 'Exit Date' },
                              { key: 'entryPrice', header: 'Entry Price', format: (v: number) => `$${v?.toFixed(2) ?? ''}` },
                              { key: 'exitPrice', header: 'Exit Price', format: (v: number) => v ? `$${v.toFixed(2)}` : '-' },
                              { key: 'returnPercent', header: 'Return %', format: (v: number) => `${v?.toFixed(2) ?? ''}%` },
                              { key: 'holdingDays', header: 'Holding Days' },
                            ]}
                            filename={`backtest-${result.strategy_name ?? 'trades'}`}
                          />
                        </div>
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
        </TabsContent>

        {/* ================================================================ */}
        {/* History Tab */}
        {/* ================================================================ */}
        <TabsContent value="history">
          <BacktestHistory onCompare={handleCompare} />
        </TabsContent>

        {/* ================================================================ */}
        {/* Comparison Tab */}
        {/* ================================================================ */}
        <TabsContent value="comparison">
          {compareEntries.length >= 2 ? (
            <BacktestComparison entries={compareEntries} onBack={handleBackFromComparison} />
          ) : (
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <GitCompare className="h-12 w-12 mb-4 opacity-50" />
                  <p className="text-lg mb-2">No comparison selected</p>
                  <p className="text-sm mb-4">Select 2-3 backtests from the History tab to compare them.</p>
                  <Button variant="outline" onClick={() => setActiveTab('history')}>
                    <History className="h-4 w-4 mr-2" />
                    Go to History
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ================================================================ */}
        {/* Parameter Sweep Tab */}
        {/* ================================================================ */}
        <TabsContent value="sweep">
          <ParameterSweep />
        </TabsContent>

        {/* ================================================================ */}
        {/* Walk-Forward Validation Tab */}
        {/* ================================================================ */}
        <TabsContent value="walkforward">
          <WalkForward />
        </TabsContent>
      </Tabs>
    </div>
  );
}
