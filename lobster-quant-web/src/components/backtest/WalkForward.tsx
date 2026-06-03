'use client';

import { useState } from 'react';
import { useWalkForward, type WalkForwardParams, type WalkForwardResult, type WindowMetrics } from '@/hooks/useBacktest';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, Play, TrendingUp, TrendingDown, ShieldCheck, ShieldAlert } from 'lucide-react';

// ============================================================================
// Helpers
// ============================================================================

function pct(value: number, decimals = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

function num(value: number, decimals = 2): string {
  return value.toFixed(decimals);
}

function MetricRow({ label, isValue, oosValue, format }: {
  label: string;
  isValue: number;
  oosValue: number;
  format: (v: number) => string;
}) {
  const delta = oosValue - isValue;
  const isPositive = delta > 0;

  return (
    <tr className="border-b">
      <td className="py-2 font-medium">{label}</td>
      <td className="py-2 text-right">{format(isValue)}</td>
      <td className="py-2 text-right">{format(oosValue)}</td>
      <td className={`py-2 text-right font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
        {isPositive ? '+' : ''}{format(delta)}
      </td>
    </tr>
  );
}

function VerdictBadge({ consistencyRatio, avgDegradation }: {
  consistencyRatio: number;
  avgDegradation: number;
}) {
  const isRobust = consistencyRatio >= 0.6 && avgDegradation < 0.3;
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
      isRobust
        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
        : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
    }`}>
      {isRobust ? <ShieldCheck className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
      {isRobust ? 'Robust Strategy' : 'Potential Overfitting'}
    </div>
  );
}

// ============================================================================
// Component
// ============================================================================

export function WalkForward() {
  const wfMutation = useWalkForward();

  const [symbol, setSymbol] = useState('');
  const [trainMonths, setTrainMonths] = useState('12');
  const [testMonths, setTestMonths] = useState('3');
  const [stepMonths, setStepMonths] = useState('3');
  const [holdingDays, setHoldingDays] = useState('20');
  const [minScore, setMinScore] = useState('60');

  const handleRun = () => {
    const params: WalkForwardParams = {
      symbol: symbol.trim().toUpperCase(),
      trainMonths: Number(trainMonths),
      testMonths: Number(testMonths),
      stepMonths: Number(stepMonths),
      holdingDays: Number(holdingDays),
      minScore: Number(minScore),
    };
    wfMutation.mutate(params);
  };

  const result = wfMutation.data ?? null;

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Walk-Forward Validation</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="wf-symbol">Stock Symbol</Label>
                <Input
                  id="wf-symbol"
                  placeholder="e.g. AAPL"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="wf-train">Train Period (months)</Label>
                <Input
                  id="wf-train"
                  type="number"
                  min={3}
                  max={36}
                  value={trainMonths}
                  onChange={(e) => setTrainMonths(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="wf-test">Test Period (months)</Label>
                <Input
                  id="wf-test"
                  type="number"
                  min={1}
                  max={12}
                  value={testMonths}
                  onChange={(e) => setTestMonths(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="wf-step">Step Size (months)</Label>
                <Input
                  id="wf-step"
                  type="number"
                  min={1}
                  max={12}
                  value={stepMonths}
                  onChange={(e) => setStepMonths(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="wf-holding">Holding Days</Label>
                <Input
                  id="wf-holding"
                  type="number"
                  min={5}
                  max={100}
                  value={holdingDays}
                  onChange={(e) => setHoldingDays(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="wf-score">Min Score</Label>
                <Input
                  id="wf-score"
                  type="number"
                  min={0}
                  max={100}
                  value={minScore}
                  onChange={(e) => setMinScore(e.target.value)}
                />
              </div>
            </div>

            <Button
              onClick={handleRun}
              disabled={!symbol.trim() || wfMutation.isPending}
            >
              {wfMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Run Walk-Forward Analysis
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {wfMutation.error && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-destructive text-center py-4">
              {wfMutation.error.message}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Summary Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Walk-Forward Summary — {result.symbol}</CardTitle>
                <VerdictBadge
                  consistencyRatio={result.consistencyRatio}
                  avgDegradation={result.avgDegradation}
                />
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Total Windows</p>
                  <p className="text-2xl font-bold">{result.totalWindows}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Avg IS Sharpe</p>
                  <p className="text-2xl font-bold">{num(result.avgIsSharpe)}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Avg OOS Sharpe</p>
                  <p className={`text-2xl font-bold ${result.avgOosSharpe > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {num(result.avgOosSharpe)}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Consistency</p>
                  <p className={`text-2xl font-bold ${result.consistencyRatio >= 0.6 ? 'text-green-600' : 'text-red-600'}`}>
                    {pct(result.consistencyRatio, 0)}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4 pt-4 border-t">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Avg Degradation</p>
                  <p className={`text-lg font-semibold ${result.avgDegradation < 0.3 ? 'text-green-600' : 'text-red-600'}`}>
                    {pct(result.avgDegradation)}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Avg OOS Win Rate</p>
                  <p className="text-lg font-semibold">{pct(result.avgOosWinRate)}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Avg OOS Return</p>
                  <p className={`text-lg font-semibold ${result.avgOosReturn > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {pct(result.avgOosReturn)}
                  </p>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t text-sm text-muted-foreground">
                Configuration: {result.trainMonths}m train / {result.testMonths}m test / {result.stepMonths}m step
              </div>
            </CardContent>
          </Card>

          {/* Per-Window Details */}
          {result.windows.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Window Details (IS vs OOS)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">#</th>
                        <th className="text-left py-2">Train Period</th>
                        <th className="text-left py-2">Test Period</th>
                        <th className="text-right py-2">IS Sharpe</th>
                        <th className="text-right py-2">OOS Sharpe</th>
                        <th className="text-right py-2">IS Return</th>
                        <th className="text-right py-2">OOS Return</th>
                        <th className="text-right py-2">IS Win%</th>
                        <th className="text-right py-2">OOS Win%</th>
                        <th className="text-right py-2">Degrad.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.windows.map((w) => (
                        <tr key={w.windowIndex} className="border-b">
                          <td className="py-2">{w.windowIndex + 1}</td>
                          <td className="py-2 text-xs">{w.trainStart} → {w.trainEnd}</td>
                          <td className="py-2 text-xs">{w.testStart} → {w.testEnd}</td>
                          <td className="py-2 text-right">{num(w.isMetrics.sharpeRatio)}</td>
                          <td className={`py-2 text-right ${w.oosMetrics.sharpeRatio > 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {num(w.oosMetrics.sharpeRatio)}
                          </td>
                          <td className="py-2 text-right">{pct(w.isMetrics.cumulativeReturn)}</td>
                          <td className={`py-2 text-right ${w.oosMetrics.cumulativeReturn > 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {pct(w.oosMetrics.cumulativeReturn)}
                          </td>
                          <td className="py-2 text-right">{pct(w.isMetrics.winRate, 0)}</td>
                          <td className="py-2 text-right">{pct(w.oosMetrics.winRate, 0)}</td>
                          <td className={`py-2 text-right ${w.degradation < 0.3 ? 'text-green-600' : 'text-red-600'}`}>
                            {pct(w.degradation)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* IS vs OOS Comparison Table */}
          {result.windows.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>IS vs OOS Aggregate Comparison</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">Metric</th>
                        <th className="text-right py-2">In-Sample (Avg)</th>
                        <th className="text-right py-2">Out-of-Sample (Avg)</th>
                        <th className="text-right py-2">Delta</th>
                      </tr>
                    </thead>
                    <tbody>
                      <MetricRow
                        label="Sharpe Ratio"
                        isValue={result.avgIsSharpe}
                        oosValue={result.avgOosSharpe}
                        format={(v) => num(v)}
                      />
                      <MetricRow
                        label="Win Rate"
                        isValue={avgMetric(result.windows, 'isMetrics', 'winRate')}
                        oosValue={avgMetric(result.windows, 'oosMetrics', 'winRate')}
                        format={(v) => pct(v, 0)}
                      />
                      <MetricRow
                        label="Cumulative Return"
                        isValue={avgMetric(result.windows, 'isMetrics', 'cumulativeReturn')}
                        oosValue={avgMetric(result.windows, 'oosMetrics', 'cumulativeReturn')}
                        format={(v) => pct(v)}
                      />
                      <MetricRow
                        label="Max Drawdown"
                        isValue={avgMetric(result.windows, 'isMetrics', 'maxDrawdown')}
                        oosValue={avgMetric(result.windows, 'oosMetrics', 'maxDrawdown')}
                        format={(v) => pct(v)}
                      />
                      <MetricRow
                        label="Profit Factor"
                        isValue={avgMetric(result.windows, 'isMetrics', 'profitFactor')}
                        oosValue={avgMetric(result.windows, 'oosMetrics', 'profitFactor')}
                        format={(v) => num(v)}
                      />
                      <MetricRow
                        label="Sortino Ratio"
                        isValue={avgMetric(result.windows, 'isMetrics', 'sortinoRatio')}
                        oosValue={avgMetric(result.windows, 'oosMetrics', 'sortinoRatio')}
                        format={(v) => num(v)}
                      />
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Empty state */}
      {!result && !wfMutation.isPending && !wfMutation.error && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <TrendingUp className="h-12 w-12 mb-4 opacity-50" />
              <p className="text-lg mb-2">No walk-forward results yet</p>
              <p className="text-sm">Enter a symbol and run the analysis to test strategy robustness</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// Helpers for aggregate comparison
// ============================================================================

function avgMetric(
  windows: WalkForwardResult['windows'],
  period: 'isMetrics' | 'oosMetrics',
  key: keyof WindowMetrics,
): number {
  if (windows.length === 0) return 0;
  const sum = windows.reduce((acc, w) => acc + (w[period][key] as number), 0);
  return sum / windows.length;
}
