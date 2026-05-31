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
    <div className="container mx-auto py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold">Simulation Dashboard</h1>
            <HelpTooltip helpKey="simulation.title" />
          </div>
          <p className="text-muted-foreground mt-2">
            Track daily simulation results and performance
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={runAllSimulations} disabled={isRunning} variant="outline">
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
          <Button onClick={runSimulation} disabled={isRunning || !selectedStrategyId}>
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
        </div>
      </div>

      {error && (
        <ErrorState 
          message={error.message} 
          onRetry={() => {
            runSimulationMutation.reset();
            runAllSimulationsMutation.reset();
          }}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        <div className="lg:col-span-2">
          <label className="text-sm font-medium mb-2 block">Strategy</label>
          <StrategySelector value={selectedStrategyId} onChange={setSelectedStrategyId} />
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">Market</label>
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

      {selectedStrategyId && (
        <div className="mb-8">
          <PerformanceMetricsCards data={performance} />
        </div>
      )}

      {selectedStrategyId && (
        <div className="mb-8">
          {chartLoading ? (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  <span className="ml-3">Loading chart...</span>
                </div>
              </CardContent>
            </Card>
          ) : chartData ? (
            <SimulationEquityCurve data={chartData} />
          ) : null}
        </div>
      )}

      {tradesLoading ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <span className="ml-3">Loading trades...</span>
            </div>
          </CardContent>
        </Card>
      ) : selectedStrategyId ? (
        <Tabs defaultValue="trades">
          <div className="flex items-center justify-between mb-4">
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
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <p className="text-lg mb-2">Select a strategy to view trades</p>
              <p className="text-sm">Choose a strategy from the dropdown above</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
