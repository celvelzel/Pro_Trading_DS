'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { Search, Moon, Sun, Menu } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export function Header() {
  const [searchQuery, setSearchQuery] = useState('')
  const [isDark, setIsDark] = useState(false)
  const router = useRouter()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      router.push(`/analysis/${searchQuery.trim().toUpperCase()}`)
      setSearchQuery('')
    }
  }

  const toggleTheme = () => {
    setIsDark(!isDark)
    document.documentElement.classList.toggle('dark')
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-bg-surface/60">
      <div className="flex h-14 items-center px-4 md:px-6">
        {/* Mobile menu button */}
        <Button variant="ghost" size="icon" className="md:hidden mr-2">
          <Menu className="h-5 w-5" />
          <span className="sr-only">Toggle menu</span>
        </Button>

        {/* Search bar */}
        <form onSubmit={handleSearch} className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-text-tertiary" />
            <Input
              type="search"
              placeholder="Search stock symbol (e.g., AAPL)..."
              className="pl-8 bg-bg-card"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </form>

        {/* Right side actions */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Theme toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="text-text-secondary"
          >
            {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            <span className="sr-only">Toggle theme</span>
          </Button>
        </div>
      </div>
    </header>
  )
}
