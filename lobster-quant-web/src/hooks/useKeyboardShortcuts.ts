'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface KeyboardShortcut {
  key: string
  ctrl?: boolean
  meta?: boolean
  action: () => void
  description: string
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const ctrlOrMeta = shortcut.ctrl || shortcut.meta
        
        if (
          e.key === shortcut.key &&
          (!ctrlOrMeta || e.ctrlKey || e.metaKey)
        ) {
          e.preventDefault()
          shortcut.action()
          return
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [shortcuts])
}

export function useGlobalKeyboardShortcuts() {
  const router = useRouter()

  const shortcuts: KeyboardShortcut[] = [
    {
      key: 'k',
      ctrl: true,
      meta: true,
      action: () => {
        const searchInput = document.querySelector('input[type="search"]') as HTMLInputElement
        searchInput?.focus()
      },
      description: 'Focus search',
    },
    {
      key: '1',
      ctrl: true,
      meta: true,
      action: () => router.push('/dashboard'),
      description: 'Go to Dashboard',
    },
    {
      key: '2',
      ctrl: true,
      meta: true,
      action: () => router.push('/scanner'),
      description: 'Go to Scanner',
    },
    {
      key: '3',
      ctrl: true,
      meta: true,
      action: () => router.push('/analysis'),
      description: 'Go to Analysis',
    },
    {
      key: '4',
      ctrl: true,
      meta: true,
      action: () => router.push('/strategy'),
      description: 'Go to Strategy',
    },
    {
      key: '5',
      ctrl: true,
      meta: true,
      action: () => router.push('/backtest'),
      description: 'Go to Backtest',
    },
    {
      key: '6',
      ctrl: true,
      meta: true,
      action: () => router.push('/simulation'),
      description: 'Go to Simulation',
    },
  ]

  useKeyboardShortcuts(shortcuts)
}
