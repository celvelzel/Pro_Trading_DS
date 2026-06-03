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
  Target,
  Play,
  Bell,
  List,
} from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'

interface MobileMenuDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

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
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
  },
]

export function MobileMenuDrawer({ open, onOpenChange }: MobileMenuDrawerProps) {
  const pathname = usePathname()

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-[280px] sm:w-[350px] p-0">
        <SheetHeader className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 bg-primary rounded-lg">
              <TrendingUp className="w-5 h-5 text-primary-foreground" />
            </div>
            <SheetTitle className="text-lg font-semibold text-text-primary">Lobster Quant</SheetTitle>
          </div>
        </SheetHeader>
        <div className="flex flex-col py-4">
          <nav className="px-3 space-y-1">
            {navItems.map((item) => {
              const isActive = pathname.startsWith(item.href)
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => onOpenChange(false)}
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
        </div>
      </SheetContent>
    </Sheet>
  )
}
