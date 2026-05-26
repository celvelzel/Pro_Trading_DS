'use client';

import { useState } from 'react';
import { StrategySelector } from '@/components/strategy';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface BacktestFormProps {
  onRun: (params: BacktestParams) => Promise<void>;
  loading?: boolean;
}

export interface BacktestParams {
  mode: 'single' | 'portfolio';
  strategyId: string;
  symbol?: string;
  symbols?: string[];
  startDate?: string;
  endDate?: string;
}

export function BacktestForm({ onRun, loading }: BacktestFormProps) {
  const [mode, setMode] = useState<'single' | 'portfolio'>('single');
  const [strategyId, setStrategyId] = useState('');
  const [symbol, setSymbol] = useState('');
  const [symbolsText, setSymbolsText] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const params: BacktestParams = {
      mode,
      strategyId,
      startDate: startDate || undefined,
      endDate: endDate || undefined,
    };

    if (mode === 'single') {
      params.symbol = symbol;
    } else {
      params.symbols = symbolsText.split(',').map(s => s.trim()).filter(Boolean);
    }

    await onRun(params);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Run Backtest</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>Strategy</Label>
            <StrategySelector value={strategyId} onChange={setStrategyId} />
          </div>

          <Tabs value={mode} onValueChange={(v) => setMode(v as 'single' | 'portfolio')}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="single">Single Stock</TabsTrigger>
              <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
            </TabsList>
            
            <TabsContent value="single" className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="symbol">Stock Symbol</Label>
                <Input
                  id="symbol"
                  placeholder="e.g., AAPL, TSLA"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  required
                />
              </div>
            </TabsContent>
            
            <TabsContent value="portfolio" className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="symbols">Stock Symbols (comma-separated)</Label>
                <Input
                  id="symbols"
                  placeholder="e.g., AAPL, TSLA, GOOG"
                  value={symbolsText}
                  onChange={(e) => setSymbolsText(e.target.value)}
                  required
                />
              </div>
            </TabsContent>
          </Tabs>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="startDate">Start Date (optional)</Label>
              <Input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="endDate">End Date (optional)</Label>
              <Input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={loading || !strategyId}>
            {loading ? 'Running Backtest...' : 'Run Backtest'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
