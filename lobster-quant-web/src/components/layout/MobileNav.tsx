'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Search,
  BarChart3,
  FlaskConical,
  Target,
  Play,
  List,
  Bell,
} from 'lucide-react'

const navItems = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: 'Watchlist',
    href: '/watchlist',
    icon: List,
  },
  {
    title: 'Scanner',
    href: '/scanner',
    icon: Search,
  },
  {
    title: 'Analysis',
    href: '/analysis',
    icon: BarChart3,
  },
  {
    title: 'Strategy',
    href: '/strategy',
    icon: Target,
  },
  {
    title: 'Backtest',
    href: '/backtest',
    icon: FlaskConical,
  },
  {
    title: 'Simulation',
    href: '/simulation',
    icon: Play,
  },
  {
    title: 'Alerts',
    href: '/alerts',
    icon: Bell,
  },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-bg-surface border-t border-gray-200 safe-bottom">
      <div className="flex justify-around items-center h-16 px-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex flex-col items-center gap-1 px-2 py-2 text-xs font-medium transition-colors min-w-0',
                isActive
                  ? 'text-primary'
                  : 'text-text-tertiary hover:text-text-primary'
              )}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              <span className="truncate">{item.title}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
