'use client';

import { Card, CardContent } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Target, BarChart3, Activity, Hash } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PerformanceMetrics } from '@/hooks/useSimulation';

interface PerformanceMetricsCardsProps {
  data: PerformanceMetrics | undefined;
}

interface MetricCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  colorClass?: string;
}

function MetricCard({ label, value, icon, colorClass = 'text-foreground' }: MetricCardProps) {
  return (
    <Card className="transition-colors hover:border-primary/30">
      <CardContent className="p-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="truncate text-[13px] font-medium text-muted-foreground">{label}</span>
          <span className="shrink-0 text-muted-foreground">{icon}</span>
        </div>
        <div className={cn('font-mono text-2xl font-semibold tracking-tight tabular-nums', colorClass)}>
          {value}
        </div>
      </CardContent>
    </Card>
  );
}

export function PerformanceMetricsCards({ data }: PerformanceMetricsCardsProps) {
  if (!data) return null;

  const returnColor = data.totalReturn >= 0 ? 'text-success' : 'text-error';
  const drawdownColor = data.maxDrawdown > 10 ? 'text-error' : 'text-foreground';

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
      <MetricCard
        label="Total Return"
        value={`${data.totalReturn >= 0 ? '+' : ''}${data.totalReturn.toFixed(2)}%`}
        icon={data.totalReturn >= 0
          ? <TrendingUp className="h-4 w-4" />
          : <TrendingDown className="h-4 w-4" />
        }
        colorClass={returnColor}
      />
      <MetricCard
        label="Win Rate"
        value={`${data.winRate.toFixed(1)}%`}
        icon={<Target className="h-4 w-4" />}
      />
      <MetricCard
        label="Sharpe Ratio"
        value={data.sharpeRatio.toFixed(2)}
        icon={<Activity className="h-4 w-4" />}
      />
      <MetricCard
        label="Max Drawdown"
        value={`${data.maxDrawdown.toFixed(2)}%`}
        icon={<BarChart3 className="h-4 w-4" />}
        colorClass={drawdownColor}
      />
      <MetricCard
        label="Volatility"
        value={`${data.volatility.toFixed(2)}%`}
        icon={<Activity className="h-4 w-4" />}
      />
      <MetricCard
        label="Total Trades"
        value={data.totalTrades.toString()}
        icon={<Hash className="h-4 w-4" />}
      />
    </div>
  );
}
