'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Search,
  BarChart3,
  FlaskConical,
  Settings,
  TrendingUp,
} from 'lucide-react'

const navItems = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
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
    title: 'Backtest',
    href: '/backtest',
    icon: FlaskConical,
  },
]

const bottomNavItems = [
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
  },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="hidden md:flex flex-col w-64 bg-bg-surface border-r border-gray-200 h-screen sticky top-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-center w-8 h-8 bg-primary rounded-lg">
          <TrendingUp className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Lobster Quant</h1>
          <p className="text-xs text-text-tertiary">v2.0 - React Edition</p>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
              )}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.title}</span>
            </Link>
          )
        })}
      </nav>

      {/* Bottom Navigation */}
      <div className="px-3 py-4 border-t border-gray-200">
        {bottomNavItems.map((item) => {
          const isActive = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
              )}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.title}</span>
            </Link>
          )
        })}
      </div>
    </aside>
  )
}
