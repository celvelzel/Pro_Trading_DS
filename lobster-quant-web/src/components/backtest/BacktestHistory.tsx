'use client';

import { useState } from 'react';
import { useBacktestHistory, useDeleteBacktestHistory, type BacktestHistoryEntry } from '@/hooks/useBacktest';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Trash2, GitCompare, RefreshCw } from 'lucide-react';

interface BacktestHistoryProps {
  onCompare: (entries: BacktestHistoryEntry[]) => void;
}

export function BacktestHistory({ onCompare }: BacktestHistoryProps) {
  const { data: history, isLoading, error, refetch } = useBacktestHistory();
  const deleteEntry = useDeleteBacktestHistory();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < 3) {
        next.add(id);
      }
      return next;
    });
  };

  const handleCompare = () => {
    if (!history) return;
    const selected = history.filter((e) => selectedIds.has(e.id));
    if (selected.length >= 2) {
      onCompare(selected);
    }
  };

  const handleDelete = (id: string) => {
    deleteEntry.mutate(id);
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-3">Loading history...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <p className="text-destructive mb-4">Failed to load history</p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!history || history.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-12 text-muted-foreground">
            <p className="text-lg mb-2">No saved backtests</p>
            <p className="text-sm">Run a backtest and save it to see it here.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Compare button */}
      {selectedIds.size >= 2 && (
        <div className="flex items-center gap-3">
          <Button onClick={handleCompare} size="sm">
            <GitCompare className="h-4 w-4 mr-2" />
            Compare {selectedIds.size} backtests
          </Button>
          <span className="text-sm text-muted-foreground">
            Select up to 3 backtests to compare
          </span>
        </div>
      )}

      {/* History list */}
      <div className="space-y-3">
        {history.map((entry) => {
          const metrics = entry.metrics as Record<string, number>;
          const isSelected = selectedIds.has(entry.id);

          return (
            <Card
              key={entry.id}
              className={`transition-colors ${isSelected ? 'border-primary' : ''}`}
            >
              <CardContent className="py-4">
                <div className="flex items-start gap-3">
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => toggleSelect(entry.id)}
                    disabled={!isSelected && selectedIds.size >= 3}
                    className="mt-1"
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{entry.symbol}</span>
                      {entry.strategyName && (
                        <span className="text-sm text-muted-foreground">
                          &middot; {entry.strategyName}
                        </span>
                      )}
                      <span className="text-xs text-muted-foreground ml-auto">
                        {new Date(entry.timestamp).toLocaleString()}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
                      {metrics.totalReturn !== undefined && (
                        <div>
                          <span className="text-muted-foreground">Return: </span>
                          <span className={metrics.totalReturn > 0 ? 'text-green-600' : 'text-red-600'}>
                            {metrics.totalReturn.toFixed(2)}%
                          </span>
                        </div>
                      )}
                      {metrics.sharpeRatio !== undefined && (
                        <div>
                          <span className="text-muted-foreground">Sharpe: </span>
                          <span>{metrics.sharpeRatio.toFixed(2)}</span>
                        </div>
                      )}
                      {metrics.winRate !== undefined && (
                        <div>
                          <span className="text-muted-foreground">Win Rate: </span>
                          <span>{metrics.winRate.toFixed(1)}%</span>
                        </div>
                      )}
                      {metrics.maxDrawdown !== undefined && (
                        <div>
                          <span className="text-muted-foreground">Max DD: </span>
                          <span className="text-red-600">{metrics.maxDrawdown.toFixed(2)}%</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(entry.id)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
