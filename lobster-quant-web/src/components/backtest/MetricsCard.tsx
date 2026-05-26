'use client';

import { useState } from 'react';
import { BacktestMetrics } from '@/stores/strategyStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface MetricsCardProps {
  metrics: BacktestMetrics;
  strategyName?: string;
}

export function MetricsCard({ metrics, strategyName }: MetricsCardProps) {
  const [expanded, setExpanded] = useState(false);

  const basicMetrics = [
    { label: 'Total Return', value: `${metrics.totalReturn.toFixed(2)}%`, highlight: metrics.totalReturn > 0 },
    { label: 'Annualized Return', value: `${metrics.annualizedReturn.toFixed(2)}%` },
    { label: 'Volatility', value: `${metrics.volatility.toFixed(2)}%` },
    { label: 'Sharpe Ratio', value: metrics.sharpeRatio.toFixed(2), highlight: metrics.sharpeRatio > 1 },
    { label: 'Max Drawdown', value: `${metrics.maxDrawdown.toFixed(2)}%`, negative: true },
    { label: 'Win Rate', value: `${metrics.winRate.toFixed(1)}%`, highlight: metrics.winRate > 50 },
  ];

  const detailedMetrics = [
    { label: 'Profit/Loss Ratio', value: metrics.profitLossRatio.toFixed(2) },
    { label: 'Total Trades', value: metrics.totalTrades.toString() },
    { label: 'Winning Trades', value: metrics.winningTrades.toString() },
    { label: 'Losing Trades', value: metrics.losingTrades.toString() },
    { label: 'Avg Holding Days', value: metrics.avgHoldingDays.toFixed(1) },
    { label: 'Avg Win', value: `${metrics.avgWin.toFixed(2)}%` },
    { label: 'Avg Loss', value: `${metrics.avgLoss.toFixed(2)}%` },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">
            {strategyName ? `${strategyName} Metrics` : 'Backtest Metrics'}
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <>
                <ChevronUp className="h-4 w-4 mr-1" />
                Less
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4 mr-1" />
                More
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {basicMetrics.map((metric) => (
            <div key={metric.label} className="space-y-1">
              <p className="text-sm text-muted-foreground">{metric.label}</p>
              <p className={`text-lg font-semibold ${
                metric.highlight ? 'text-green-600' : 
                metric.negative ? 'text-red-600' : ''
              }`}>
                {metric.value}
              </p>
            </div>
          ))}
        </div>

        {expanded && (
          <div className="mt-6 pt-4 border-t">
            <h4 className="text-sm font-medium text-muted-foreground mb-4">Detailed Metrics</h4>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {detailedMetrics.map((metric) => (
                <div key={metric.label} className="space-y-1">
                  <p className="text-sm text-muted-foreground">{metric.label}</p>
                  <p className="text-base font-medium">{metric.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
