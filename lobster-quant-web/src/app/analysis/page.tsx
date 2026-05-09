'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PrefetchLink } from '@/components/ui/prefetch-link'
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
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Stock Analysis</h1>
        <p className="text-text-secondary mt-1">
          Deep analysis with technical indicators, options data, and trading signals
        </p>
      </div>

      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle>Analyze a Stock</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAnalyze} className="flex gap-4">
            <div className="flex-1">
              <Input
                type="text"
                placeholder="Enter stock symbol (e.g., AAPL, MSFT, TSLA)"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="text-lg"
              />
            </div>
            <Button type="submit" size="lg">
              <Search className="w-5 h-5 mr-2" />
              Analyze
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Quick Access - uses PrefetchLink for instant navigation */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {QUICK_ACCESS_STOCKS.map((stock) => (
          <PrefetchLink
            key={stock.symbol}
            symbol={stock.symbol}
            href={`/analysis/${stock.symbol}`}
            className="block"
          >
            <Card className="cursor-pointer hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">{stock.symbol}</p>
                    <p className="text-sm text-text-secondary">{stock.name}</p>
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
