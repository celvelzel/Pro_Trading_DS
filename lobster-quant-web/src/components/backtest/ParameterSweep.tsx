'use client';

import { useState } from 'react';
import { useBacktestSweep, type SweepParams, type SweepResponse } from '@/hooks/useBacktest';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, Play, TrendingUp, TrendingDown } from 'lucide-react';

const SWEEPABLE_PARAMS = [
  { value: 'holdingDays', label: 'Holding Days', min: 5, max: 100, step: 5, defaultMin: 10, defaultMax: 40 },
  { value: 'minScore', label: 'Min Score', min: 0, max: 100, step: 5, defaultMin: 40, defaultMax: 80 },
] as const;

type ParamName = (typeof SWEEPABLE_PARAMS)[number]['value'];

export function ParameterSweep() {
  const sweepMutation = useBacktestSweep();

  const [symbol, setSymbol] = useState('');
  const [paramName, setParamName] = useState<ParamName>('holdingDays');
  const [min, setMin] = useState('10');
  const [max, setMax] = useState('40');
  const [step, setStep] = useState('5');

  const selectedParam = SWEEPABLE_PARAMS.find((p) => p.value === paramName)!;

  const handleParamChange = (name: ParamName) => {
    setParamName(name);
    const p = SWEEPABLE_PARAMS.find((pp) => pp.value === name)!;
    setMin(String(p.defaultMin));
    setMax(String(p.defaultMax));
    setStep(String(p.step));
  };

  const handleRun = () => {
    const params: SweepParams = {
      symbol: symbol.trim().toUpperCase(),
      parameterName: paramName,
      min: Number(min),
      max: Number(max),
      step: Number(step),
    };
    sweepMutation.mutate(params);
  };

  const result = sweepMutation.data ?? null;

  // Find best result for highlighting
  const bestIdx = result
    ? result.results.reduce((best, item, idx) => {
        if (best === -1) return idx;
        const bestReturn = result.results[best].metrics.totalReturn ?? -Infinity;
        const curReturn = item.metrics.totalReturn ?? -Infinity;
        return curReturn > bestReturn ? idx : best;
      }, -1)
    : -1;

  return (
    <div className="space-y-6">
      {/* Sweep Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Parameter Sweep Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="sweep-symbol">Stock Symbol</Label>
                <Input
                  id="sweep-symbol"
                  placeholder="e.g., AAPL"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label>Parameter to Sweep</Label>
                <div className="flex gap-2">
                  {SWEEPABLE_PARAMS.map((p) => (
                    <Button
                      key={p.value}
                      variant={paramName === p.value ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleParamChange(p.value)}
                    >
                      {p.label}
                    </Button>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="sweep-min">Min ({selectedParam.label})</Label>
                <Input
                  id="sweep-min"
                  type="number"
                  min={selectedParam.min}
                  max={selectedParam.max}
                  value={min}
                  onChange={(e) => setMin(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sweep-max">Max ({selectedParam.label})</Label>
                <Input
                  id="sweep-max"
                  type="number"
                  min={selectedParam.min}
                  max={selectedParam.max}
                  value={max}
                  onChange={(e) => setMax(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sweep-step">Step</Label>
                <Input
                  id="sweep-step"
                  type="number"
                  min={1}
                  value={step}
                  onChange={(e) => setStep(e.target.value)}
                />
              </div>
            </div>

            <Button
              onClick={handleRun}
              disabled={!symbol.trim() || sweepMutation.isPending}
            >
              {sweepMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running sweep...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Sweep
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {sweepMutation.error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">{sweepMutation.error.message}</p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Results Table */}
          <Card>
            <CardHeader>
              <CardTitle>
                Sweep Results: {result.symbol} &middot; {selectedParam.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {result.results.length === 0 ? (
                <p className="text-muted-foreground py-4">No results. Check your parameters.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2 pr-4">{selectedParam.label}</th>
                        <th className="text-right py-2 px-3">Total Return</th>
                        <th className="text-right py-2 px-3">Sharpe Ratio</th>
                        <th className="text-right py-2 px-3">Win Rate</th>
                        <th className="text-right py-2 px-3">Max Drawdown</th>
                        <th className="text-right py-2 px-3">Trades</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.results.map((item, idx) => {
                        const m = item.metrics;
                        const isBest = idx === bestIdx;

                        return (
                          <tr
                            key={item.paramValue}
                            className={`border-b ${isBest ? 'bg-green-50 dark:bg-green-950/20' : ''}`}
                          >
                            <td className="py-2 pr-4 font-medium">
                              {item.paramValue}
                              {isBest && (
                                <span className="ml-2 text-xs text-green-600 font-semibold">
                                  BEST
                                </span>
                              )}
                            </td>
                            <td className={`text-right py-2 px-3 ${
                              (m.totalReturn ?? 0) > 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {(m.totalReturn ?? 0).toFixed(2)}%
                            </td>
                            <td className="text-right py-2 px-3">
                              {(m.sharpeRatio ?? 0).toFixed(2)}
                            </td>
                            <td className="text-right py-2 px-3">
                              {(m.winRate ?? 0).toFixed(1)}%
                            </td>
                            <td className="text-right py-2 px-3 text-red-600">
                              {(m.maxDrawdown ?? 0).toFixed(2)}%
                            </td>
                            <td className="text-right py-2 px-3">
                              {m.totalTrades ?? 0}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Simple SVG line chart for totalReturn vs param */}
          {result.results.length >= 2 && (
            <Card>
              <CardHeader>
                <CardTitle>Total Return vs {selectedParam.label}</CardTitle>
              </CardHeader>
              <CardContent>
                <SweepLineChart
                  results={result.results}
                  paramLabel={selectedParam.label}
                />
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

/** Simple SVG line chart for sweep results. */
function SweepLineChart({
  results,
  paramLabel,
}: {
  results: NonNullable<SweepResponse>['results'];
  paramLabel: string;
}) {
  const width = 600;
  const height = 250;
  const pad = { top: 20, right: 20, bottom: 40, left: 60 };

  const returns = results.map((r) => r.metrics.totalReturn ?? 0);
  const minRet = Math.min(...returns);
  const maxRet = Math.max(...returns);
  const retRange = maxRet - minRet || 1;

  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const points = results
    .map((r, i) => {
      const x = pad.left + (i / (results.length - 1)) * plotW;
      const ret = r.metrics.totalReturn ?? 0;
      const y = pad.top + (1 - (ret - minRet) / retRange) * plotH;
      return `${x},${y}`;
    })
    .join(' ');

  // Zero line
  const zeroY = pad.top + (1 - (0 - minRet) / retRange) * plotH;
  const hasZero = minRet <= 0 && maxRet >= 0;

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="border rounded">
      {/* Y-axis grid */}
      {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
        const y = pad.top + (1 - pct) * plotH;
        const val = minRet + pct * retRange;
        return (
          <g key={pct}>
            <line
              x1={pad.left}
              y1={y}
              x2={width - pad.right}
              y2={y}
              stroke="#e5e7eb"
              strokeDasharray="4,4"
            />
            <text
              x={pad.left - 8}
              y={y + 4}
              textAnchor="end"
              className="text-[10px] fill-muted-foreground"
            >
              {val.toFixed(1)}%
            </text>
          </g>
        );
      })}

      {/* Zero line */}
      {hasZero && (
        <line
          x1={pad.left}
          y1={zeroY}
          x2={width - pad.right}
          y2={zeroY}
          stroke="#9ca3af"
          strokeWidth="1"
        />
      )}

      {/* Data line */}
      <polyline points={points} fill="none" stroke="#3b82f6" strokeWidth="2" />

      {/* Data points */}
      {results.map((r, i) => {
        const x = pad.left + (i / (results.length - 1)) * plotW;
        const ret = r.metrics.totalReturn ?? 0;
        const y = pad.top + (1 - (ret - minRet) / retRange) * plotH;
        return (
          <circle key={i} cx={x} cy={y} r="4" fill="#3b82f6" />
        );
      })}

      {/* X-axis labels */}
      {results.map((r, i) => {
        const x = pad.left + (i / (results.length - 1)) * plotW;
        return (
          <text
            key={i}
            x={x}
            y={height - 8}
            textAnchor="middle"
            className="text-[10px] fill-muted-foreground"
          >
            {r.paramValue}
          </text>
        );
      })}

      {/* X-axis label */}
      <text
        x={pad.left + plotW / 2}
        y={height - 0}
        textAnchor="middle"
        className="text-[11px] fill-muted-foreground"
      >
        {paramLabel}
      </text>
    </svg>
  );
}
