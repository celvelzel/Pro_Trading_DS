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

/**
 * Returns true when the active element is a text-input context
 * where single-key shortcuts should NOT fire.
 */
function isInputFocused(): boolean {
  const el = document.activeElement
  if (!el) return false
  const tag = el.tagName.toLowerCase()
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return true
  return (el as HTMLElement).isContentEditable
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const modifierPressed = e.ctrlKey || e.metaKey

        // If shortcut needs modifier but it's not held → skip
        const needsModifier = shortcut.ctrl || shortcut.meta
        if (needsModifier && !modifierPressed) continue

        // Skip plain-key shortcuts when user is typing in an input
        if (!needsModifier && isInputFocused()) continue

        if (e.key === shortcut.key) {
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

  /** Dispatch a custom event that the ShortcutsHelp dialog listens for. */
  const toggleHelp = () => {
    window.dispatchEvent(new CustomEvent('shortcuts-help:toggle'))
  }

  const shortcuts: KeyboardShortcut[] = [
    // ── Cmd/Ctrl+K → focus search ──
    {
      key: 'k',
      ctrl: true,
      meta: true,
      action: () => {
        const searchInput = document.querySelector(
          'input[type="search"]',
        ) as HTMLInputElement
        searchInput?.focus()
      },
      description: 'Focus search',
    },

    // ── ? → toggle help ──
    {
      key: '?',
      action: toggleHelp,
      description: 'Show shortcuts',
    },

    // ── Ctrl/Cmd + number → page navigation (modifier required) ──
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
    {
      key: '7',
      ctrl: true,
      meta: true,
      action: () => router.push('/alerts'),
      description: 'Go to Alerts',
    },

    // ── Plain number keys 1-7 → sidebar page switch (no modifier) ──
    {
      key: '1',
      action: () => router.push('/dashboard'),
      description: 'Go to Dashboard',
    },
    {
      key: '2',
      action: () => router.push('/scanner'),
      description: 'Go to Scanner',
    },
    {
      key: '3',
      action: () => router.push('/analysis'),
      description: 'Go to Analysis',
    },
    {
      key: '4',
      action: () => router.push('/strategy'),
      description: 'Go to Strategy',
    },
    {
      key: '5',
      action: () => router.push('/backtest'),
      description: 'Go to Backtest',
    },
    {
      key: '6',
      action: () => router.push('/simulation'),
      description: 'Go to Simulation',
    },
    {
      key: '7',
      action: () => router.push('/alerts'),
      description: 'Go to Alerts',
    },
  ]

  useKeyboardShortcuts(shortcuts)
}
