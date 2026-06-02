'use client'

import { memo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Link from 'next/link'
import { Search, FlaskConical, List, Settings, BarChart3 } from 'lucide-react'
import { cn } from '@/lib/utils'

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
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {ACTIONS.map((action) => {
            const Icon = action.icon
            return (
              <Link
                key={action.href}
                href={action.href}
                className={cn(
                  'flex flex-col items-center gap-2 p-3 rounded-lg border border-border',
                  'hover:border-primary hover:bg-primary/5 transition-colors',
                  'group'
                )}
              >
                <Icon className="w-5 h-5 text-text-secondary group-hover:text-primary transition-colors" />
                <span className="text-sm font-medium text-text-primary">{action.label}</span>
                <span className="text-xs text-text-secondary text-center leading-tight">{action.description}</span>
              </Link>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
})
