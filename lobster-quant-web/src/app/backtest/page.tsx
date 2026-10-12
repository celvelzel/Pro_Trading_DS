'use client';

import { useState, useCallback } from 'react';
import { BacktestForm, BacktestParams, MetricsCard } from '@/components/backtest';
import { BacktestHistory } from '@/components/backtest/BacktestHistory';
import { BacktestComparison } from '@/components/backtest/BacktestComparison';
import { ParameterSweep } from '@/components/backtest/ParameterSweep';
import { WalkForward } from '@/components/backtest/WalkForward';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { HelpTooltip } from '@/components/ui/help-tooltip';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import { EmptyState } from '@/components/ui/empty-state';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/layout/PageHeader';
import { useRunBacktest, type BacktestHistoryEntry, type BacktestPageResult } from '@/hooks/useBacktest';
import { showToastError } from '@/hooks/useApiQuery';
import { History, GitCompare, SlidersHorizontal, Play, TrendingUp } from 'lucide-react';
import { ExportButton } from '@/components/ui/export-button';
import { cn } from '@/lib/utils';

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
  const [, setLocalHistory] = useState<BacktestHistoryEntry[]>(() => loadLocalHistory());

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
    <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
      <PageHeader
        title="Strategy Backtest"
        description="Test your strategies against historical data"
        actions={<HelpTooltip helpKey="backtest.title" />}
      />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="line" className="mb-4">
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
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
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
                        <Table>
                          <TableHeader>
                            <TableRow className="hover:bg-transparent">
                              <TableHead className="text-xs font-medium text-muted-foreground">Entry Date</TableHead>
                              <TableHead className="text-xs font-medium text-muted-foreground">Exit Date</TableHead>
                              <TableHead className="text-right text-xs font-medium text-muted-foreground">Entry Price</TableHead>
                              <TableHead className="text-right text-xs font-medium text-muted-foreground">Exit Price</TableHead>
                              <TableHead className="text-right text-xs font-medium text-muted-foreground">Return</TableHead>
                              <TableHead className="text-right text-xs font-medium text-muted-foreground">Days</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {result.trades.map((trade, i) => (
                              <TableRow key={i}>
                                <TableCell className="font-mono text-sm">{trade.entryDate}</TableCell>
                                <TableCell className="font-mono text-sm">{trade.exitDate || '-'}</TableCell>
                                <TableCell className="text-right font-mono text-sm">${trade.entryPrice?.toFixed(2)}</TableCell>
                                <TableCell className="text-right font-mono text-sm">${trade.exitPrice?.toFixed(2) || '-'}</TableCell>
                                <TableCell className={cn(
                                  'text-right font-mono text-sm font-medium',
                                  trade.returnPercent > 0 ? 'text-success' : 'text-error'
                                )}>
                                  {trade.returnPercent?.toFixed(2)}%
                                </TableCell>
                                <TableCell className="text-right font-mono text-sm">{trade.holdingDays}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>
                  )}

                  {result.equityCurve.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Equity Curve</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
                          Chart placeholder - integrate with your charting library
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </>
              )}

              {!loading && !result && !error && (
                <EmptyState
                  icon="chart"
                  title="No backtest results yet"
                  message="Select a strategy and run a backtest to see results"
                />
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
              <CardContent className="pt-4">
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
