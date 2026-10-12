'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useStrategyStore, StrategyParams } from '@/stores/strategyStore';
import { StrategyForm } from '@/components/strategy';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BacktestRecord {
  id: string;
  symbol: string;
  startDate: string;
  endDate: string;
  totalTrades: number;
  winRate: number;
  totalReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  createdAt: string;
}

interface SimulationTrade {
  id: string;
  symbol: string;
  entryDate: string;
  entryPrice: number;
  exitDate: string | null;
  exitPrice: number | null;
  shares: number;
  status: string;
  pnl: number | null;
  pnlPercent: number | null;
}

interface SimulationSnapshot {
  date: string;
  portfolioValue: number;
  cash: number;
  invested: number;
  openTrades: number;
  closedTrades: number;
}

interface SignalRecord {
  id: string;
  ruleId: string;
  symbol: string;
  condition: string;
  threshold: number;
  currentValue: number;
  message: string;
  triggeredAt: string;
  read: boolean;
}

interface SignalStats {
  totalSignals: number;
  lookbackDays: number;
  evaluated5d: number;
  evaluated10d: number;
  evaluated20d: number;
  winRate5d: number;
  winRate10d: number;
  winRate20d: number;
  avgReturn5d: number;
  avgReturn10d: number;
  avgReturn20d: number;
  bySignalType: Record<string, {
    count: number;
    winRate5d: number;
    winRate10d: number;
    winRate20d: number;
    avgReturn5d: number;
    avgReturn10d: number;
    avgReturn20d: number;
  }>;
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function StrategyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const {
    selectedStrategy,
    loading,
    error,
    fetchStrategy,
    updateStrategy,
    clearError,
  } = useStrategyStore();

  // Tab data state
  const [backtests, setBacktests] = useState<BacktestRecord[]>([]);
  const [simulations, setSimulations] = useState<{
    trades: SimulationTrade[];
    snapshots: SimulationSnapshot[];
  }>({ trades: [], snapshots: [] });
  const [signals, setSignals] = useState<SignalRecord[]>([]);
  const [signalStats, setSignalStats] = useState<SignalStats | null>(null);
  const [tabLoading, setTabLoading] = useState<Record<string, boolean>>({});
  const [tabErrors, setTabErrors] = useState<Record<string, string | null>>({});

  // Fetch strategy on mount
  useEffect(() => {
    if (id) {
      fetchStrategy(id);
    }
  }, [id, fetchStrategy]);

  // Fetch tab data
  const fetchTabData = useCallback(async (tab: string) => {
    if (!id) return;
    setTabLoading((prev) => ({ ...prev, [tab]: true }));
    setTabErrors((prev) => ({ ...prev, [tab]: null }));

    try {
      if (tab === 'backtests') {
        const res = await fetch(`${API_BASE}/strategy/${id}/backtests`);
        if (!res.ok) throw new Error('Failed to fetch backtests');
        setBacktests(await res.json());
      } else if (tab === 'simulations') {
        const res = await fetch(`${API_BASE}/strategy/${id}/simulations`);
        if (!res.ok) throw new Error('Failed to fetch simulations');
        setSimulations(await res.json());
      } else if (tab === 'signals') {
        const res = await fetch(`${API_BASE}/strategy/${id}/signals`);
        if (!res.ok) throw new Error('Failed to fetch signals');
        setSignals(await res.json());
      } else if (tab === 'performance') {
        const res = await fetch(`${API_BASE}/signals/stats?lookback=30d&strategy_id=${id}`);
        if (!res.ok) throw new Error('Failed to fetch signal stats');
        setSignalStats(await res.json());
      }
    } catch (err) {
      setTabErrors((prev) => ({ ...prev, [tab]: (err as Error).message }));
    } finally {
      setTabLoading((prev) => ({ ...prev, [tab]: false }));
    }
  }, [id]);

  // Handle tab change
  const handleTabChange = (tab: string) => {
    if (tab !== 'parameters' && !tabLoading[tab]) {
      fetchTabData(tab);
    }
  };

  // Handle strategy update
  const handleUpdate = async (name: string, description: string, params: StrategyParams) => {
    if (selectedStrategy) {
      await updateStrategy(selectedStrategy.id, { name, description, params });
    }
  };

  // Loading state
  if (loading && !selectedStrategy) {
    return (
      <div className="mx-auto flex min-h-[400px] w-full max-w-[1600px] items-center justify-center p-4 md:p-6">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (error && !selectedStrategy) {
    return (
      <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
        <div className="flex items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={clearError}>
            Dismiss
          </Button>
        </div>
      </div>
    );
  }

  // Not found
  if (!selectedStrategy) {
    return (
      <div className="mx-auto w-full max-w-[1600px] p-4 py-12 text-center text-sm text-muted-foreground md:p-6">
        Strategy not found.
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => router.push('/strategy')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-lg font-semibold leading-tight tracking-tight text-foreground">
              {selectedStrategy.name}
            </h1>
            {selectedStrategy.isPreset && <Badge variant="secondary">Preset</Badge>}
            <Badge variant="outline">{selectedStrategy.logic}</Badge>
          </div>
        </div>
        <p className="text-[13px] leading-snug text-muted-foreground">
          {selectedStrategy.description || 'No description'}
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="parameters" onValueChange={handleTabChange}>
        <TabsList variant="line">
          <TabsTrigger value="parameters">Parameters</TabsTrigger>
          <TabsTrigger value="backtests">Backtests</TabsTrigger>
          <TabsTrigger value="simulations">Simulations</TabsTrigger>
          <TabsTrigger value="signals">Signals</TabsTrigger>
          <TabsTrigger value="performance">Live Performance</TabsTrigger>
        </TabsList>

        {/* Parameters Tab */}
        <TabsContent value="parameters" className="mt-6">
          <StrategyForm
            strategy={selectedStrategy}
            onSubmit={handleUpdate}
            onCancel={() => {}}
          />
        </TabsContent>

        {/* Backtests Tab */}
        <TabsContent value="backtests" className="mt-6">
          <BacktestsTab
            backtests={backtests}
            loading={tabLoading.backtests}
            error={tabErrors.backtests}
            onRetry={() => fetchTabData('backtests')}
          />
        </TabsContent>

        {/* Simulations Tab */}
        <TabsContent value="simulations" className="mt-6">
          <SimulationsTab
            trades={simulations.trades}
            snapshots={simulations.snapshots}
            loading={tabLoading.simulations}
            error={tabErrors.simulations}
            onRetry={() => fetchTabData('simulations')}
          />
        </TabsContent>

        {/* Signals Tab */}
        <TabsContent value="signals" className="mt-6">
          <SignalsTab
            signals={signals}
            loading={tabLoading.signals}
            error={tabErrors.signals}
            onRetry={() => fetchTabData('signals')}
          />
        </TabsContent>

        {/* Live Performance Tab */}
        <TabsContent value="performance" className="mt-6">
          <LivePerformanceTab
            stats={signalStats}
            loading={tabLoading.performance}
            error={tabErrors.performance}
            onRetry={() => fetchTabData('performance')}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab Components
// ---------------------------------------------------------------------------

function TabLoadingState() {
  return (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  );
}

function TabErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="py-12 text-center">
      <p className="mb-2 text-sm text-destructive">{error}</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}

function TabEmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
      {children}
    </div>
  );
}

function BacktestsTab({
  backtests,
  loading,
  error,
  onRetry,
}: {
  backtests: BacktestRecord[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  if (loading) {
    return <TabLoadingState />;
  }

  if (error) {
    return <TabErrorState error={error} onRetry={onRetry} />;
  }

  if (backtests.length === 0) {
    return <TabEmptyState>No backtest results yet for this strategy.</TabEmptyState>;
  }

  return (
    <div className="space-y-4">
      {backtests.map((bt) => (
        <Card key={bt.id}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="font-mono">{bt.symbol}</CardTitle>
              <Badge variant={bt.totalReturn >= 0 ? 'success' : 'destructive'}>
                {bt.totalReturn >= 0 ? '+' : ''}{bt.totalReturn}%
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
              <div>
                <span className="text-muted-foreground">Trades:</span>{' '}
                <span className="font-mono font-medium">{bt.totalTrades}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Win Rate:</span>{' '}
                <span className="font-mono font-medium">{bt.winRate}%</span>
              </div>
              <div>
                <span className="text-muted-foreground">Max DD:</span>{' '}
                <span className="font-mono font-medium text-error">{bt.maxDrawdown}%</span>
              </div>
              <div>
                <span className="text-muted-foreground">Sharpe:</span>{' '}
                <span className="font-mono font-medium">{bt.sharpeRatio}</span>
              </div>
            </div>
            <div className="mt-2 font-mono text-xs text-muted-foreground">
              {bt.startDate} → {bt.endDate}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function SimulationsTab({
  trades,
  snapshots,
  loading,
  error,
  onRetry,
}: {
  trades: SimulationTrade[];
  snapshots: SimulationSnapshot[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  if (loading) {
    return <TabLoadingState />;
  }

  if (error) {
    return <TabErrorState error={error} onRetry={onRetry} />;
  }

  if (trades.length === 0 && snapshots.length === 0) {
    return <TabEmptyState>No simulation data yet for this strategy.</TabEmptyState>;
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      {snapshots.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Latest Snapshot</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
              <div>
                <span className="text-muted-foreground">Portfolio:</span>{' '}
                <span className="font-mono font-medium">{'$'}{snapshots[0].portfolioValue.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Cash:</span>{' '}
                <span className="font-mono font-medium">{'$'}{snapshots[0].cash.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Open Trades:</span>{' '}
                <span className="font-mono font-medium">{snapshots[0].openTrades}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Date:</span>{' '}
                <span className="font-mono font-medium">{snapshots[0].date}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Trades */}
      {trades.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Trades</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {trades.slice(0, 20).map((trade) => (
                <div
                  key={trade.id}
                  className="flex items-center justify-between rounded-md border-b border-border py-2 transition-colors last:border-0 hover:bg-muted/50"
                >
                  <div>
                    <span className="font-mono font-medium">{trade.symbol}</span>
                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                      {trade.entryDate} → {trade.exitDate || 'Open'}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <Badge variant={trade.status === 'open' ? 'secondary' : 'outline'}>
                      {trade.status}
                    </Badge>
                    {trade.pnlPercent != null && (
                      <span
                        className={cn(
                          'font-mono font-medium',
                          trade.pnlPercent >= 0 ? 'text-success' : 'text-error'
                        )}
                      >
                        {trade.pnlPercent >= 0 ? '+' : ''}{trade.pnlPercent.toFixed(2)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function LivePerformanceTab({
  stats,
  loading,
  error,
  onRetry,
}: {
  stats: SignalStats | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  if (loading) {
    return <TabLoadingState />;
  }

  if (error) {
    return <TabErrorState error={error} onRetry={onRetry} />;
  }

  if (!stats || stats.totalSignals === 0) {
    return (
      <TabEmptyState>
        No signal data yet. Signals will be tracked automatically as they are generated.
      </TabEmptyState>
    );
  }

  const signalTypes = Object.keys(stats.bySignalType);

  return (
    <div className="space-y-6">
      {/* Overall Win Rates */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Win Rate Overview (Last {stats.lookbackDays} Days)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-border bg-background p-4 text-center">
              <div className="font-mono text-2xl font-semibold tracking-tight">{stats.totalSignals}</div>
              <div className="mt-1 text-sm text-muted-foreground">Total Signals</div>
            </div>
            <div className="rounded-lg border border-border bg-background p-4 text-center">
              <div className={cn('font-mono text-2xl font-semibold tracking-tight', stats.winRate5d >= 50 ? 'text-success' : 'text-error')}>
                {stats.winRate5d}%
              </div>
              <div className="mt-1 text-sm text-muted-foreground">5-Day Win Rate</div>
              <div className="mt-1 font-mono text-xs text-muted-foreground">
                {stats.evaluated5d} evaluated
              </div>
            </div>
            <div className="rounded-lg border border-border bg-background p-4 text-center">
              <div className={cn('font-mono text-2xl font-semibold tracking-tight', stats.winRate10d >= 50 ? 'text-success' : 'text-error')}>
                {stats.winRate10d}%
              </div>
              <div className="mt-1 text-sm text-muted-foreground">10-Day Win Rate</div>
              <div className="mt-1 font-mono text-xs text-muted-foreground">
                {stats.evaluated10d} evaluated
              </div>
            </div>
            <div className="rounded-lg border border-border bg-background p-4 text-center">
              <div className={cn('font-mono text-2xl font-semibold tracking-tight', stats.winRate20d >= 50 ? 'text-success' : 'text-error')}>
                {stats.winRate20d}%
              </div>
              <div className="mt-1 text-sm text-muted-foreground">20-Day Win Rate</div>
              <div className="mt-1 font-mono text-xs text-muted-foreground">
                {stats.evaluated20d} evaluated
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Average Returns */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Average Returns</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-border bg-background p-4 text-center">
              <div className={cn('font-mono text-xl font-semibold tracking-tight', stats.avgReturn5d >= 0 ? 'text-success' : 'text-error')}>
                {stats.avgReturn5d >= 0 ? '+' : ''}{stats.avgReturn5d}%
              </div>
              <div className="mt-1 text-sm text-muted-foreground">5-Day Avg Return</div>
            </div>
            <div className="rounded-lg border border-border bg-background p-4 text-center">
              <div className={cn('font-mono text-xl font-semibold tracking-tight', stats.avgReturn10d >= 0 ? 'text-success' : 'text-error')}>
                {stats.avgReturn10d >= 0 ? '+' : ''}{stats.avgReturn10d}%
              </div>
              <div className="mt-1 text-sm text-muted-foreground">10-Day Avg Return</div>
            </div>
            <div className="rounded-lg border border-border bg-background p-4 text-center">
              <div className={cn('font-mono text-xl font-semibold tracking-tight', stats.avgReturn20d >= 0 ? 'text-success' : 'text-error')}>
                {stats.avgReturn20d >= 0 ? '+' : ''}{stats.avgReturn20d}%
              </div>
              <div className="mt-1 text-sm text-muted-foreground">20-Day Avg Return</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* By Signal Type */}
      {signalTypes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Performance by Signal Type</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {signalTypes.map((type) => {
                const typeStats = stats.bySignalType[type];
                return (
                  <div key={type} className="rounded-lg border border-border bg-background p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant={type === '强烈推荐' ? 'default' : type === '推荐' ? 'secondary' : 'outline'}>
                          {type}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          {typeStats.count} signal{typeStats.count !== 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">5d WR:</span>{' '}
                        <span className={cn('font-mono font-medium', typeStats.winRate5d >= 50 ? 'text-success' : 'text-error')}>
                          {typeStats.winRate5d}%
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">10d WR:</span>{' '}
                        <span className={cn('font-mono font-medium', typeStats.winRate10d >= 50 ? 'text-success' : 'text-error')}>
                          {typeStats.winRate10d}%
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">20d WR:</span>{' '}
                        <span className={cn('font-mono font-medium', typeStats.winRate20d >= 50 ? 'text-success' : 'text-error')}>
                          {typeStats.winRate20d}%
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">5d Ret:</span>{' '}
                        <span className={cn('font-mono font-medium', typeStats.avgReturn5d >= 0 ? 'text-success' : 'text-error')}>
                          {typeStats.avgReturn5d >= 0 ? '+' : ''}{typeStats.avgReturn5d}%
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">10d Ret:</span>{' '}
                        <span className={cn('font-mono font-medium', typeStats.avgReturn10d >= 0 ? 'text-success' : 'text-error')}>
                          {typeStats.avgReturn10d >= 0 ? '+' : ''}{typeStats.avgReturn10d}%
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">20d Ret:</span>{' '}
                        <span className={cn('font-mono font-medium', typeStats.avgReturn20d >= 0 ? 'text-success' : 'text-error')}>
                          {typeStats.avgReturn20d >= 0 ? '+' : ''}{typeStats.avgReturn20d}%
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function SignalsTab({
  signals,
  loading,
  error,
  onRetry,
}: {
  signals: SignalRecord[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  if (loading) {
    return <TabLoadingState />;
  }

  if (error) {
    return <TabErrorState error={error} onRetry={onRetry} />;
  }

  if (signals.length === 0) {
    return <TabEmptyState>No signals triggered yet for this strategy.</TabEmptyState>;
  }

  return (
    <div className="space-y-3">
      {signals.map((signal) => (
        <Card key={signal.id}>
          <CardContent className="pt-4">
            <div className="mb-2 flex items-center justify-between">
              <div className="font-mono font-semibold">{signal.symbol}</div>
              <Badge variant={signal.read ? 'outline' : 'default'}>
                {signal.read ? 'Read' : 'New'}
              </Badge>
            </div>
            <p className="mb-2 text-sm text-muted-foreground">{signal.message}</p>
            <div className="flex flex-wrap items-center gap-4 font-mono text-xs text-muted-foreground">
              <span>Condition: {signal.condition}</span>
              <span>Threshold: {signal.threshold}</span>
              <span>Current: {signal.currentValue}</span>
              <span>{signal.triggeredAt}</span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
