'use client'

import { useGlobalKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'

export function KeyboardShortcutsProvider({ children }: { children: React.ReactNode }) {
  useGlobalKeyboardShortcuts()
  return <>{children}</>
}
