'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  BarChart3,
  List,
  Bell,
  Briefcase,
} from 'lucide-react'

/** Primary destinations for the bottom tab bar; the full menu lives in the drawer. */
const navItems = [
  { title: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { title: 'Watchlist', href: '/watchlist', icon: List },
  { title: 'Analysis', href: '/analysis', icon: BarChart3 },
  { title: 'Portfolio', href: '/portfolio', icon: Briefcase },
  { title: 'Alerts', href: '/alerts', icon: Bell },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:hidden safe-bottom"
    >
      <div className="flex h-14 items-stretch justify-around px-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-md text-[10px] font-medium transition-colors',
                isActive
                  ? 'text-primary'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <item.icon className="size-5 shrink-0" strokeWidth={isActive ? 2.4 : 2} />
              <span className="truncate">{item.title}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
