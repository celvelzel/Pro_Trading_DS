'use client'

import { memo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Link from 'next/link'
import { Search, FlaskConical, List, Settings, BarChart3 } from 'lucide-react'

interface QuickAction {
  label: string
  href: string
  icon: React.ElementType
  description: string
}

const ACTIONS: QuickAction[] = [
  {
    label: 'Scanner',
    href: '/scanner',
    icon: Search,
    description: 'Scan for trading signals',
  },
  {
    label: 'Backtest',
    href: '/backtest',
    icon: FlaskConical,
    description: 'Test strategies on historical data',
  },
  {
    label: 'Watchlist',
    href: '/dashboard',
    icon: List,
    description: 'Manage your stock watchlist',
  },
  {
    label: 'Strategy',
    href: '/strategy',
    icon: BarChart3,
    description: 'View and manage strategies',
  },
  {
    label: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Configure app settings',
  },
]

export const QuickActionsCard = memo(function QuickActionsCard() {
  return (
    <Card className="transition-colors hover:border-primary/30">
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-0.5">
          {ACTIONS.map((action) => {
            const Icon = action.icon
            return (
              <Link
                key={action.href}
                href={action.href}
                className="group flex items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-bg-hover"
              >
                <div className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-muted-foreground transition-colors group-hover:border-primary/30 group-hover:bg-accent group-hover:text-primary">
                  <Icon className="size-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium leading-tight text-foreground">{action.label}</p>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">{action.description}</p>
                </div>
              </Link>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
})
