'use client';

import { Card, CardContent } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Target, BarChart3, Activity, Hash } from 'lucide-react';
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
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-3">
          <div className="text-muted-foreground">{icon}</div>
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className={`text-2xl font-bold ${colorClass}`}>{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function PerformanceMetricsCards({ data }: PerformanceMetricsCardsProps) {
  if (!data) return null;

  const returnColor = data.totalReturn >= 0 ? 'text-green-600' : 'text-red-600';
  const drawdownColor = data.maxDrawdown > 10 ? 'text-red-600' : 'text-foreground';

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      <MetricCard
        label="Total Return"
        value={`${data.totalReturn >= 0 ? '+' : ''}${data.totalReturn.toFixed(2)}%`}
        icon={data.totalReturn >= 0
          ? <TrendingUp className="h-5 w-5" />
          : <TrendingDown className="h-5 w-5" />
        }
        colorClass={returnColor}
      />
      <MetricCard
        label="Win Rate"
        value={`${data.winRate.toFixed(1)}%`}
        icon={<Target className="h-5 w-5" />}
      />
      <MetricCard
        label="Sharpe Ratio"
        value={data.sharpeRatio.toFixed(2)}
        icon={<Activity className="h-5 w-5" />}
      />
      <MetricCard
        label="Max Drawdown"
        value={`${data.maxDrawdown.toFixed(2)}%`}
        icon={<BarChart3 className="h-5 w-5" />}
        colorClass={drawdownColor}
      />
      <MetricCard
        label="Volatility"
        value={`${data.volatility.toFixed(2)}%`}
        icon={<Activity className="h-5 w-5" />}
      />
      <MetricCard
        label="Total Trades"
        value={data.totalTrades.toString()}
        icon={<Hash className="h-5 w-5" />}
      />
    </div>
  );
}
