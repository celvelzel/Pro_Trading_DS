'use client'

import { memo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { ArrowRight, TrendingUp, TrendingDown, Minus, Clock } from 'lucide-react'
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
    BUY: { label: 'BUY', color: 'text-success bg-success/10', icon: TrendingUp },
    SELL: { label: 'SELL', color: 'text-error bg-error/10', icon: TrendingDown },
    NEUTRAL: { label: 'NEUTRAL', color: 'text-text-secondary bg-text-secondary/10', icon: Minus },
  }

  const { label, color, icon: Icon } = config[signal]

  return (
    <span className={cn('flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', color)}>
      <Icon className="w-3 h-3" />
      {label}
    </span>
  )
}

export const SignalFeedCard = memo(function SignalFeedCard() {
  return (
    <Card className="flex flex-col h-full animate-in fade-in slide-in-from-bottom-2 duration-500">
      <CardHeader className="pb-3 border-b border-border/50">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Clock className="w-4 h-4 text-primary" />
            Signal Change Feed
          </CardTitle>
          <span className="text-[10px] font-medium text-text-secondary uppercase tracking-tighter bg-muted px-1.5 py-0.5 rounded">
            Live Updates
          </span>
        </div>
      </CardHeader>
      <CardContent className="p-0 flex-1 overflow-auto max-h-[400px]">
        {MOCK_SIGNAL_CHANGES.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-text-secondary">
            <p className="text-sm">No recent signal changes</p>
          </div>
        ) : (
          <div className="divide-y divide-border/30">
            {MOCK_SIGNAL_CHANGES.map((change) => (
              <div key={change.id} className="p-3 hover:bg-muted/30 transition-colors group">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-bold text-sm text-text-primary tracking-tight group-hover:text-primary transition-colors">
                    {change.symbol}
                  </span>
                  <span className="text-[10px] text-text-secondary font-medium">
                    {formatDistanceToNow(new Date(change.timestamp), { addSuffix: true })}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <SignalBadge signal={change.oldSignal} />
                  <ArrowRight className="w-3 h-3 text-text-secondary/50" />
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
