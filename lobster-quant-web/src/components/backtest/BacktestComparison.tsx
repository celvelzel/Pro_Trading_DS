'use client';

import { useMemo } from 'react';
import type { BacktestHistoryEntry } from '@/hooks/useBacktest';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, TrendingUp, TrendingDown } from 'lucide-react';

interface BacktestComparisonProps {
  entries: BacktestHistoryEntry[];
  onBack: () => void;
}

const CHART_COLORS = ['#3b82f6', '#ef4444', '#22c55e'];

const METRIC_LABELS: Record<string, string> = {
  totalReturn: 'Total Return',
  annualizedReturn: 'Annualized Return',
  sharpeRatio: 'Sharpe Ratio',
  maxDrawdown: 'Max Drawdown',
  winRate: 'Win Rate',
  totalTrades: 'Total Trades',
  volatility: 'Volatility',
  profitLossRatio: 'P/L Ratio',
};

function findBest(
  entries: BacktestHistoryEntry[],
  key: string,
  higher: boolean
): string | null {
  let bestId: string | null = null;
  let bestVal = higher ? -Infinity : Infinity;

  for (const entry of entries) {
    const val = (entry.metrics as Record<string, number>)[key];
    if (val === undefined) continue;
    if (higher ? val > bestVal : val < bestVal) {
      bestVal = val;
      bestId = entry.id;
    }
  }
  return bestId;
}

export function BacktestComparison({ entries, onBack }: BacktestComparisonProps) {
  // Compute which entry is best for each metric
  const bestMap = useMemo(() => {
    const map: Record<string, Record<string, boolean>> = {};
    for (const entry of entries) {
      map[entry.id] = {};
    }

    const higherBetter = ['totalReturn', 'annualizedReturn', 'sharpeRatio', 'winRate', 'profitLossRatio'];
    const lowerBetter = ['maxDrawdown', 'volatility'];

    for (const key of [...higherBetter, ...lowerBetter]) {
      const higher = higherBetter.includes(key);
      const bestId = findBest(entries, key, higher);
      if (bestId && map[bestId]) {
        map[bestId][key] = true;
      }
    }
    return map;
  }, [entries]);

  // Equity curve overlay using SVG
  const equityCurves = useMemo(() => {
    return entries.map((entry, idx) => {
      const curve = entry.equityCurve as Array<{ date?: string; value?: number } | number>;
      if (!curve || curve.length === 0) return null;

      const values = curve.map((p) =>
        typeof p === 'number' ? p : (p.value ?? 1)
      );

      const minVal = Math.min(...values);
      const maxVal = Math.max(...values);
      const range = maxVal - minVal || 1;

      return {
        id: entry.id,
        symbol: entry.symbol,
        color: CHART_COLORS[idx % CHART_COLORS.length],
        values,
        minVal,
        maxVal,
        range,
      };
    }).filter(Boolean);
  }, [entries]);

  const chartWidth = 700;
  const chartHeight = 250;
  const padding = { top: 20, right: 20, bottom: 30, left: 50 };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="outline" size="sm" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to History
        </Button>
        <h3 className="text-lg font-semibold">
          Comparing {entries.length} backtests
        </h3>
      </div>

      {/* Equity Curve Overlay */}
      <Card>
        <CardHeader>
          <CardTitle>Equity Curves</CardTitle>
        </CardHeader>
        <CardContent>
          {equityCurves.length > 0 ? (
            <div>
              {/* Legend */}
              <div className="flex gap-4 mb-4">
                {equityCurves.map((curve) => curve && (
                  <div key={curve.id} className="flex items-center gap-2 text-sm">
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: curve.color }}
                    />
                    <span>{curve.symbol}</span>
                  </div>
                ))}
              </div>

              <svg
                width="100%"
                viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                className="border rounded"
              >
                {/* Grid lines */}
                {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
                  const y = padding.top + (1 - pct) * (chartHeight - padding.top - padding.bottom);
                  return (
                    <g key={pct}>
                      <line
                        x1={padding.left}
                        y1={y}
                        x2={chartWidth - padding.right}
                        y2={y}
                        stroke="#e5e7eb"
                        strokeDasharray="4,4"
                      />
                      <text
                        x={padding.left - 8}
                        y={y + 4}
                        textAnchor="end"
                        className="text-[10px] fill-muted-foreground"
                      >
                        {(pct * 100).toFixed(0)}%
                      </text>
                    </g>
                  );
                })}

                {/* Equity curves */}
                {equityCurves.map((curve) => {
                  if (!curve || curve.values.length < 2) return null;

                  const plotW = chartWidth - padding.left - padding.right;
                  const plotH = chartHeight - padding.top - padding.bottom;
                  const stepX = plotW / (curve.values.length - 1);

                  const points = curve.values
                    .map((v, i) => {
                      const x = padding.left + i * stepX;
                      const normalized = (v - curve.minVal) / curve.range;
                      const y = padding.top + (1 - normalized) * plotH;
                      return `${x},${y}`;
                    })
                    .join(' ');

                  return (
                    <polyline
                      key={curve.id}
                      points={points}
                      fill="none"
                      stroke={curve.color}
                      strokeWidth="2"
                    />
                  );
                })}
              </svg>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No equity curve data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Comparison Table */}
      <Card>
        <CardHeader>
          <CardTitle>Metrics Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 pr-4 font-medium">Metric</th>
                  {entries.map((entry, idx) => (
                    <th
                      key={entry.id}
                      className="text-right py-2 px-3 font-medium"
                    >
                      <div className="flex items-center justify-end gap-2">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }}
                        />
                        {entry.symbol}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(METRIC_LABELS).map(([key, label]) => {
                  const hasAny = entries.some(
                    (e) => (e.metrics as Record<string, number>)[key] !== undefined
                  );
                  if (!hasAny) return null;

                  return (
                    <tr key={key} className="border-b">
                      <td className="py-2 pr-4 text-muted-foreground">{label}</td>
                      {entries.map((entry) => {
                        const val = (entry.metrics as Record<string, number>)[key];
                        const isBest = bestMap[entry.id]?.[key];
                        const isNegative = key === 'maxDrawdown';

                        return (
                          <td
                            key={entry.id}
                            className={`text-right py-2 px-3 ${
                              isBest
                                ? isNegative
                                  ? 'text-green-600 font-semibold'
                                  : 'text-green-600 font-semibold'
                                : ''
                            }`}
                          >
                            {val !== undefined ? (
                              <span className="inline-flex items-center gap-1">
                                {isBest && (
                                  <span className="text-green-600">
                                    {isNegative ? (
                                      <TrendingDown className="h-3 w-3" />
                                    ) : (
                                      <TrendingUp className="h-3 w-3" />
                                    )}
                                  </span>
                                )}
                                {key.includes('Rate') || key.includes('Return') || key.includes('Drawdown') || key === 'volatility'
                                  ? `${val.toFixed(2)}%`
                                  : key === 'totalTrades'
                                  ? val.toString()
                                  : val.toFixed(2)}
                              </span>
                            ) : (
                              '-'
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
