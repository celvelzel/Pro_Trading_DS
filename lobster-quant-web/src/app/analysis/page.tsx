'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PrefetchLink } from '@/components/ui/prefetch-link'
import { PageHeader } from '@/components/layout/PageHeader'
import { Search, BarChart3 } from 'lucide-react'

const QUICK_ACCESS_STOCKS = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'MSFT', name: 'Microsoft Corp.' },
  { symbol: 'TSLA', name: 'Tesla Inc.' },
  { symbol: 'GOOG', name: 'Alphabet Inc.' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.' },
  { symbol: 'QQQ', name: 'Invesco QQQ Trust' },
]

export default function AnalysisPage() {
  const [symbol, setSymbol] = useState('')
  const router = useRouter()

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault()
    if (symbol.trim()) {
      router.push(`/analysis/${symbol.trim().toUpperCase()}`)
    }
  }

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
      {/* Page Header */}
      <PageHeader
        title="Stock Analysis"
        description="Deep analysis with technical indicators, options data, and trading signals"
      />

      {/* Search Form */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Analyze a Stock</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAnalyze} className="flex flex-col gap-3 sm:flex-row">
            <div className="flex-1">
              <Input
                type="text"
                placeholder="Enter stock symbol (e.g., AAPL, MSFT, TSLA)"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="h-9 font-mono uppercase"
              />
            </div>
            <Button type="submit" className="h-9">
              <Search className="mr-2 size-4" />
              Analyze
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Quick Access - uses PrefetchLink for instant navigation */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {QUICK_ACCESS_STOCKS.map((stock) => (
          <PrefetchLink
            key={stock.symbol}
            symbol={stock.symbol}
            href={`/analysis/${stock.symbol}`}
            className="block"
          >
            <Card className="h-full cursor-pointer transition-colors hover:border-primary/40">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <BarChart3 className="size-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-mono font-medium text-foreground">{stock.symbol}</p>
                    <p className="truncate text-sm text-muted-foreground">{stock.name}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </PrefetchLink>
        ))}
      </div>
    </div>
  )
}
