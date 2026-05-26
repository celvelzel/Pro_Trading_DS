'use client';

import { useState, useEffect } from 'react';
import { useStrategyStore, Strategy } from '@/stores/strategyStore';
import { StrategySelector } from '@/components/strategy';
import { TradeList } from '@/components/simulation/TradeList';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Play, RefreshCw } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

interface SimulatedTrade {
  id: string;
  symbol: string;
  entryDate: string;
  entryPrice: number;
  exitDate?: string;
  exitPrice?: number;
  shares: number;
  status: 'open' | 'closed';
  pnl?: number;
  pnlPercent?: number;
}

interface PerformanceMetrics {
  strategyId: string;
  window: string;
  totalReturn: number;
  volatility: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  totalTrades: number;
}

export default function SimulationPage() {
  const { strategies, fetchStrategies } = useStrategyStore();
  const [selectedStrategyId, setSelectedStrategyId] = useState('');
  const [market, setMarket] = useState('US');
  const [trades, setTrades] = useState<SimulatedTrade[]>([]);
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  useEffect(() => {
    if (selectedStrategyId) {
      fetchTrades();
      fetchPerformance();
    }
  }, [selectedStrategyId]);

  const fetchTrades = async () => {
    if (!selectedStrategyId) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/simulation/simulation/trades?strategy_id=${selectedStrategyId}`);
      if (!response.ok) throw new Error('Failed to fetch trades');
      const data = await response.json();
      setTrades(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const fetchPerformance = async () => {
    if (!selectedStrategyId) return;
    
    try {
      const response = await fetch(`${API_BASE}/simulation/simulation/performance?strategy_id=${selectedStrategyId}&window=1M`);
      if (!response.ok) throw new Error('Failed to fetch performance');
      const data = await response.json();
      setPerformance(data);
    } catch (err) {
      console.error('Failed to fetch performance:', err);
    }
  };

  const runSimulation = async () => {
    if (!selectedStrategyId) return;
    
    setRunning(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/simulation/simulation/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategyId: selectedStrategyId,
          market: market,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Simulation failed');
      }
      
      // Refresh data after simulation
      await fetchTrades();
      await fetchPerformance();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const runAllSimulations = async () => {
    setRunning(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/simulation/simulation/run-all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ market }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Simulation failed');
      }
      
      // Refresh data
      if (selectedStrategyId) {
        await fetchTrades();
        await fetchPerformance();
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="container mx-auto py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Simulation Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Track daily simulation results and performance
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={runAllSimulations} disabled={running} variant="outline">
            <RefreshCw className={`h-4 w-4 mr-2 ${running ? 'animate-spin' : ''}`} />
            Run All
          </Button>
          <Button onClick={runSimulation} disabled={running || !selectedStrategyId}>
            <Play className={`h-4 w-4 mr-2 ${running ? 'animate-spin' : ''}`} />
            Run Selected
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive p-4 rounded-lg mb-6">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        <div className="lg:col-span-2">
          <label className="text-sm font-medium mb-2 block">Strategy</label>
          <StrategySelector value={selectedStrategyId} onChange={setSelectedStrategyId} />
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">Market</label>
          <Select value={market} onValueChange={setMarket}>
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Total Return</p>
              <p className={`text-2xl font-bold ${
                (performance?.totalReturn || 0) >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {performance?.totalReturn?.toFixed(2) || '0.00'}%
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Win Rate</p>
              <p className="text-2xl font-bold">
                {performance?.winRate?.toFixed(1) || '0.0'}%
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
              <p className="text-2xl font-bold">
                {performance?.sharpeRatio?.toFixed(2) || '0.00'}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Total Trades</p>
              <p className="text-2xl font-bold">
                {performance?.totalTrades || 0}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {loading ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <span className="ml-3">Loading trades...</span>
            </div>
          </CardContent>
        </Card>
      ) : selectedStrategyId ? (
        <TradeList trades={trades} />
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
