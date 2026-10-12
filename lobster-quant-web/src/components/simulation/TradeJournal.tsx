'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, TrendingUp, TrendingDown, Clock } from 'lucide-react';
import type { TradeJournalEntry } from '@/hooks/useSimulation';

interface TradeJournalProps {
  entries: TradeJournalEntry[];
}

function TradeJournalItem({ entry }: { entry: TradeJournalEntry }) {
  const [expanded, setExpanded] = useState(false);
  const isClosed = entry.status === 'closed';
  const isProfit = (entry.pnl ?? 0) >= 0;

  return (
    <div className="mb-2 overflow-hidden rounded-lg border border-border">
      {/* Summary row - always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50"
      >
        <div className="flex-shrink-0 text-muted-foreground">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </div>

        {/* Symbol + direction icon */}
        <div className="flex min-w-[80px] items-center gap-2">
          {isProfit ? (
            <TrendingUp className="h-4 w-4 text-success" />
          ) : (
            <TrendingDown className="h-4 w-4 text-error" />
          )}
          <span className="font-mono font-semibold">{entry.symbol}</span>
        </div>

        {/* Entry date */}
        <span className="min-w-[100px] font-mono text-sm text-muted-foreground tabular-nums">
          {entry.entryDate}
        </span>

        {/* Status badge */}
        <Badge variant={isClosed ? 'outline' : 'default'} className="min-w-[60px] justify-center">
          {entry.status}
        </Badge>

        {/* P&L */}
        <div className="flex-1 text-right">
          {isClosed ? (
            <span className={`font-mono font-medium tabular-nums ${isProfit ? 'text-success' : 'text-error'}`}>
              {isProfit ? '+' : ''}{entry.pnl?.toFixed(2)} ({entry.pnlPercent?.toFixed(1)}%)
            </span>
          ) : (
            <span className="text-muted-foreground text-sm">Open</span>
          )}
        </div>

        {/* Holding days */}
        {entry.holdingDays !== null && entry.holdingDays !== undefined && (
          <div className="flex min-w-[60px] items-center justify-end gap-1 font-mono text-xs text-muted-foreground tabular-nums">
            <Clock className="h-3 w-3" />
            {entry.holdingDays}d
          </div>
        )}
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-border bg-muted/30 px-4 pb-4 pt-3">
          <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
            {/* Entry details */}
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Entry</p>
              <p className="font-mono font-medium tabular-nums">${entry.entryPrice.toFixed(2)}</p>
              <p className="font-mono text-xs text-muted-foreground tabular-nums">{entry.shares} shares</p>
            </div>

            {/* Exit details */}
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Exit</p>
              {entry.exitPrice ? (
                <>
                  <p className="font-mono font-medium tabular-nums">${entry.exitPrice.toFixed(2)}</p>
                  <p className="font-mono text-xs text-muted-foreground tabular-nums">{entry.exitDate}</p>
                </>
              ) : (
                <p className="text-muted-foreground">—</p>
              )}
            </div>

            {/* Entry signal */}
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Entry Signal</p>
              {entry.entryScore !== null && entry.entryScore !== undefined ? (
                <div className="flex items-center gap-2">
                  <span className="font-mono font-medium tabular-nums">{entry.entryScore.toFixed(0)}</span>
                  {entry.entrySignalType && (
                    <Badge variant="outline" className="text-xs">
                      {entry.entrySignalType}
                    </Badge>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground">—</p>
              )}
            </div>

            {/* Exit reason */}
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Exit Reason</p>
              <p className="font-medium">{entry.exitReason ?? '—'}</p>
            </div>
          </div>

          {/* Entry reasons */}
          {entry.entryReasons && entry.entryReasons.length > 0 && (
            <div className="mt-3">
              <p className="mb-1 text-xs text-muted-foreground">Entry Reasons</p>
              <div className="flex flex-wrap gap-1">
                {entry.entryReasons.map((reason, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">
                    {reason}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function TradeJournal({ entries }: TradeJournalProps) {
  const closedEntries = entries.filter(e => e.status === 'closed');
  const openEntries = entries.filter(e => e.status === 'open');

  if (entries.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <p className="text-lg mb-2">No trade journal entries</p>
            <p className="text-sm">Run a simulation to generate trade data</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Trade Journal
          <Badge variant="outline">{entries.length} trades</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {openEntries.length > 0 && (
          <div className="mb-4">
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">
              Open Positions ({openEntries.length})
            </h3>
            {openEntries.map(entry => (
              <TradeJournalItem key={entry.id} entry={entry} />
            ))}
          </div>
        )}

        {closedEntries.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">
              Closed Trades ({closedEntries.length})
            </h3>
            {closedEntries.map(entry => (
              <TradeJournalItem key={entry.id} entry={entry} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
