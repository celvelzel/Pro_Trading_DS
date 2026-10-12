'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { TrendingUp } from 'lucide-react'
import {
  navGroups,
  bottomNavItems,
  type NavItem,
} from '@/components/layout/nav-config'

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <Link
      href={item.href}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'group relative flex h-8 items-center gap-2.5 rounded-md px-2.5 text-[13px] transition-colors',
        active
          ? 'bg-accent font-medium text-accent-foreground'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
      )}
    >
      {active && (
        <span
          aria-hidden
          className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-primary"
        />
      )}
      <item.icon
        className={cn(
          'size-4 shrink-0 transition-colors',
          active ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
        )}
      />
      <span className="truncate">{item.title}</span>
    </Link>
  )
}

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="sticky top-0 hidden h-screen w-[232px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 border-b border-sidebar-border px-4">
        <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary shadow-sm">
          <TrendingUp className="size-4 text-primary-foreground" strokeWidth={2.5} />
        </div>
        <div className="min-w-0 leading-tight">
          <h1 className="truncate text-sm font-semibold tracking-tight text-foreground">
            Lobster Quant
          </h1>
          <p className="truncate text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
            Trading Terminal
          </p>
        </div>
      </div>

      {/* Main navigation */}
      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {navGroups.map((group) => (
          <div key={group.label}>
            <p className="mb-1.5 px-2.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground/70">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavLink
                  key={item.href}
                  item={item}
                  active={pathname.startsWith(item.href)}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom navigation */}
      <div className="border-t border-sidebar-border px-3 py-3">
        {bottomNavItems.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            active={pathname.startsWith(item.href)}
          />
        ))}
      </div>
    </aside>
  )
}
