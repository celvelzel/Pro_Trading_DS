'use client'

import { memo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { ArrowRight, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface SignalChange {
  id: string
  symbol: string
  oldSignal: 'BUY' | 'SELL' | 'NEUTRAL'
  newSignal: 'BUY' | 'SELL' | 'NEUTRAL'
  timestamp: string
}

// Mock data for the retry - keeping it simple as requested
const MOCK_SIGNAL_CHANGES: SignalChange[] = [
  { id: '1', symbol: 'AAPL', oldSignal: 'NEUTRAL', newSignal: 'BUY', timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString() },
  { id: '2', symbol: 'TSLA', oldSignal: 'BUY', newSignal: 'NEUTRAL', timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString() },
  { id: '3', symbol: 'MSFT', oldSignal: 'NEUTRAL', newSignal: 'SELL', timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString() },
  { id: '4', symbol: 'NVDA', oldSignal: 'SELL', newSignal: 'BUY', timestamp: new Date(Date.now() - 1000 * 60 * 180).toISOString() },
  { id: '5', symbol: 'AMD', oldSignal: 'BUY', newSignal: 'SELL', timestamp: new Date(Date.now() - 1000 * 60 * 240).toISOString() },
  { id: '6', symbol: 'GOOGL', oldSignal: 'NEUTRAL', newSignal: 'BUY', timestamp: new Date(Date.now() - 1000 * 60 * 300).toISOString() },
  { id: '7', symbol: 'META', oldSignal: 'BUY', newSignal: 'NEUTRAL', timestamp: new Date(Date.now() - 1000 * 60 * 360).toISOString() },
  { id: '8', symbol: 'AMZN', oldSignal: 'SELL', newSignal: 'NEUTRAL', timestamp: new Date(Date.now() - 1000 * 60 * 420).toISOString() },
]

function SignalBadge({ signal }: { signal: 'BUY' | 'SELL' | 'NEUTRAL' }) {
  const config = {
    BUY: { label: 'BUY', color: 'bg-success/10 text-success', icon: TrendingUp },
    SELL: { label: 'SELL', color: 'bg-error/10 text-error', icon: TrendingDown },
    NEUTRAL: { label: 'NEUTRAL', color: 'bg-muted text-muted-foreground', icon: Minus },
  }

  const { label, color, icon: Icon } = config[signal]

  return (
    <span className={cn('flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider', color)}>
      <Icon className="size-3" />
      {label}
    </span>
  )
}

export const SignalFeedCard = memo(function SignalFeedCard() {
  return (
    <Card className="flex h-full flex-col transition-colors hover:border-primary/30 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <CardHeader className="border-b border-border/50 pb-3">
        <div className="flex items-center justify-between">
          <CardTitle>Signal Change Feed</CardTitle>
          <span className="flex items-center gap-1.5 rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            <span className="size-1.5 rounded-full bg-success" />
            Live Updates
          </span>
        </div>
      </CardHeader>
      <CardContent className="max-h-[400px] flex-1 overflow-auto p-0">
        {MOCK_SIGNAL_CHANGES.length === 0 ? (
          <div className="flex h-40 flex-col items-center justify-center text-muted-foreground">
            <p className="text-sm">No recent signal changes</p>
          </div>
        ) : (
          <div className="divide-y divide-border/50">
            {MOCK_SIGNAL_CHANGES.map((change) => (
              <div key={change.id} className="group p-3 transition-colors hover:bg-bg-hover">
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="font-mono text-sm font-bold tracking-tight text-foreground">
                    {change.symbol}
                  </span>
                  <span className="text-[10px] font-medium text-muted-foreground">
                    {formatDistanceToNow(new Date(change.timestamp), { addSuffix: true })}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <SignalBadge signal={change.oldSignal} />
                  <ArrowRight className="size-3 text-muted-foreground/60" />
                  <SignalBadge signal={change.newSignal} />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
})
