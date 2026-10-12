'use client'

import { useState } from 'react'
import { useTheme } from 'next-themes'
import { Moon, Sun, Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { SearchAutocomplete } from '@/components/layout/SearchAutocomplete'
import { DataSourceStatus } from '@/components/ui/data-source-status'
import { MobileMenuDrawer } from '@/components/layout/MobileMenuDrawer'

export function Header() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const toggleTheme = () => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')
  }

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="flex h-14 items-center gap-3 px-4 md:px-6">
        {/* Mobile menu button */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={() => setMobileMenuOpen(true)}
        >
          <Menu className="size-5" />
          <span className="sr-only">Open navigation menu</span>
        </Button>

        <MobileMenuDrawer
          open={mobileMenuOpen}
          onOpenChange={setMobileMenuOpen}
        />

        {/* Global symbol search */}
        <SearchAutocomplete />

        {/* Right side actions */}
        <div className="ml-auto flex items-center gap-1.5">
          <DataSourceStatus />

          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label="Toggle color theme"
          >
            <Sun className="hidden size-4.5 dark:block" />
            <Moon className="size-4.5 dark:hidden" />
          </Button>
        </div>
      </div>
    </header>
  )
}
