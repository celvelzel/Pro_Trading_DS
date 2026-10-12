'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { TrendingUp } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { navGroups, bottomNavItems } from '@/components/layout/nav-config'

interface MobileMenuDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function MobileMenuDrawer({ open, onOpenChange }: MobileMenuDrawerProps) {
  const pathname = usePathname()
  const allGroups = [...navGroups, { label: 'System', items: bottomNavItems }]

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-[280px] p-0 sm:w-[320px]">
        <SheetHeader className="border-b border-border px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary">
              <TrendingUp className="size-4 text-primary-foreground" strokeWidth={2.5} />
            </div>
            <div className="min-w-0 leading-tight text-left">
              <SheetTitle className="text-sm font-semibold tracking-tight text-foreground">
                Lobster Quant
              </SheetTitle>
              <p className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                Trading Terminal
              </p>
            </div>
          </div>
        </SheetHeader>

        <nav className="space-y-5 overflow-y-auto px-3 py-4">
          {allGroups.map((group) => (
            <div key={group.label}>
              <p className="mb-1.5 px-2.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground/70">
                {group.label}
              </p>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive = pathname.startsWith(item.href)
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => onOpenChange(false)}
                      aria-current={isActive ? 'page' : undefined}
                      className={cn(
                        'flex h-9 items-center gap-2.5 rounded-md px-2.5 text-sm transition-colors',
                        isActive
                          ? 'bg-accent font-medium text-accent-foreground'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      )}
                    >
                      <item.icon
                        className={cn(
                          'size-4 shrink-0',
                          isActive ? 'text-primary' : 'text-muted-foreground'
                        )}
                      />
                      <span>{item.title}</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
