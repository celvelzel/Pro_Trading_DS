'use client';

import { useState, useEffect } from 'react';
import { useStrategyStore } from '@/stores/strategyStore';
import { StrategySelector } from '@/components/strategy';
import { TradeList } from '@/components/simulation/TradeList';
import { TradeJournal } from '@/components/simulation/TradeJournal';
import { SimulationEquityCurve } from '@/components/simulation/SimulationEquityCurve';
import { PerformanceMetricsCards } from '@/components/simulation/PerformanceMetricsCards';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { HelpTooltip } from '@/components/ui/help-tooltip';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Play, RefreshCw, Loader2 } from 'lucide-react';
import { ExportButton } from '@/components/ui/export-button';
import { ErrorState } from '@/components/ui/error-state';
import { EmptyState } from '@/components/ui/empty-state';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  useSimulationTrades,
  useSimulationPerformance,
  useSimulationJournal,
  useSimulationChart,
  useRunSimulation,
  useRunAllSimulations,
} from '@/hooks/useSimulation';
import { showToastError } from '@/hooks/useApiQuery';

export default function SimulationPage() {
  const { fetchStrategies } = useStrategyStore();
  const [selectedStrategyId, setSelectedStrategyId] = useState('');
  const [market, setMarket] = useState('US');

  // TanStack Query hooks
  const {
    data: trades = [],
    isLoading: tradesLoading,
    error: tradesError,
  } = useSimulationTrades(selectedStrategyId);

  const {
    data: performance,
    error: performanceError,
  } = useSimulationPerformance(selectedStrategyId);

  const {
    data: journalEntries = [],
  } = useSimulationJournal(selectedStrategyId);

  const {
    data: chartData,
    isLoading: chartLoading,
  } = useSimulationChart(selectedStrategyId);

  const runSimulationMutation = useRunSimulation();
  const runAllSimulationsMutation = useRunAllSimulations();

  const isRunning = runSimulationMutation.isPending || runAllSimulationsMutation.isPending;
  const error = tradesError || performanceError;

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  // Show toast on mutation errors
  useEffect(() => {
    if (runSimulationMutation.error) {
      showToastError(runSimulationMutation.error);
    }
  }, [runSimulationMutation.error]);

  useEffect(() => {
    if (runAllSimulationsMutation.error) {
      showToastError(runAllSimulationsMutation.error);
    }
  }, [runAllSimulationsMutation.error]);

  const runSimulation = () => {
    if (!selectedStrategyId) return;
    runSimulationMutation.mutate({ strategyId: selectedStrategyId, market });
  };

  const runAllSimulations = () => {
    runAllSimulationsMutation.mutate({ market });
  };

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
      <PageHeader
        title="Simulation Dashboard"
        description="Track daily simulation results and performance"
        actions={
          <>
            <HelpTooltip helpKey="simulation.title" />
            <Button onClick={runAllSimulations} disabled={isRunning} variant="outline" size="sm">
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Run All
                </>
              )}
            </Button>
            <Button onClick={runSimulation} disabled={isRunning || !selectedStrategyId} size="sm">
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Selected
                </>
              )}
            </Button>
          </>
        }
      />

      {error && (
        <ErrorState
          message={error.message}
          onRetry={() => {
            runSimulationMutation.reset();
            runAllSimulationsMutation.reset();
          }}
        />
      )}

      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
            <div className="lg:col-span-2">
              <label className="mb-2 block text-[13px] font-medium text-muted-foreground">Strategy</label>
              <StrategySelector value={selectedStrategyId} onChange={setSelectedStrategyId} />
            </div>
            <div>
              <label className="mb-2 block text-[13px] font-medium text-muted-foreground">Market</label>
              <Select value={market} onValueChange={(value) => setMarket(value || 'US')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="US">US Market</SelectItem>
                  <SelectItem value="HK">HK Market</SelectItem>
                  <SelectItem value="A">A-Share Market</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {selectedStrategyId && (
        <PerformanceMetricsCards data={performance} />
      )}

      {selectedStrategyId && (
        chartLoading ? (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-3 text-muted-foreground">Loading chart...</span>
              </div>
            </CardContent>
          </Card>
        ) : chartData ? (
          <SimulationEquityCurve data={chartData} />
        ) : null
      )}

      {tradesLoading ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="ml-3 text-muted-foreground">Loading trades...</span>
            </div>
          </CardContent>
        </Card>
      ) : selectedStrategyId ? (
        <Tabs defaultValue="trades">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TabsList>
                <TabsTrigger value="trades">Trades</TabsTrigger>
                <TabsTrigger value="journal">Journal</TabsTrigger>
              </TabsList>
              <HelpTooltip helpKey="simulation.trades" />
            </div>
            <ExportButton
              data={trades}
              columns={[
                { key: 'symbol', header: 'Symbol' },
                { key: 'status', header: 'Status' },
                { key: 'entryDate', header: 'Entry Date' },
                { key: 'entryPrice', header: 'Entry Price', format: (v: number) => `$${v?.toFixed(2) ?? ''}` },
                { key: 'exitDate', header: 'Exit Date' },
                { key: 'exitPrice', header: 'Exit Price', format: (v: number) => v ? `$${v.toFixed(2)}` : '-' },
                { key: 'shares', header: 'Shares' },
                { key: 'pnl', header: 'P&L', format: (v: number) => v != null ? `$${v.toFixed(2)}` : '-' },
                { key: 'pnlPercent', header: 'P&L %', format: (v: number) => v != null ? `${v.toFixed(2)}%` : '-' },
              ]}
              filename={`simulation-${selectedStrategyId || 'trades'}`}
            />
          </div>
          <TabsContent value="trades">
            <TradeList trades={trades} />
          </TabsContent>
          <TabsContent value="journal">
            <TradeJournal entries={journalEntries} />
          </TabsContent>
        </Tabs>
      ) : (
        <EmptyState
          icon="flask"
          title="Select a strategy to view trades"
          message="Choose a strategy from the dropdown above"
        />
      )}
    </div>
  );
}
