'use client'

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Keyboard } from 'lucide-react'

interface ShortcutGroup {
  title: string
  shortcuts: { key: string; description: string }[]
}

const shortcutGroups: ShortcutGroup[] = [
  {
    title: 'Navigation',
    shortcuts: [
      { key: '1', description: 'Dashboard' },
      { key: '2', description: 'Scanner' },
      { key: '3', description: 'Analysis' },
      { key: '4', description: 'Strategy' },
      { key: '5', description: 'Backtest' },
      { key: '6', description: 'Simulation' },
      { key: '7', description: 'Alerts' },
    ],
  },
  {
    title: 'Actions',
    shortcuts: [
      { key: '⌘/Ctrl+K', description: 'Focus search' },
      { key: '?', description: 'Show shortcuts' },
    ],
  },
]

function ShortcutKey({ children }: { children: string }) {
  return (
    <kbd className="inline-flex items-center justify-center min-w-[28px] h-6 px-1.5 rounded bg-muted border border-border font-mono text-xs text-muted-foreground">
      {children}
    </kbd>
  )
}

export function ShortcutsHelp() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const handleToggle = () => setOpen((prev) => !prev)
    const handleClose = () => setOpen(false)

    window.addEventListener('shortcuts-help:toggle', handleToggle)
    window.addEventListener('shortcuts-help:close', handleClose)
    return () => {
      window.removeEventListener('shortcuts-help:toggle', handleToggle)
      window.removeEventListener('shortcuts-help:close', handleClose)
    }
  }, [])

  return (
    <>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Keyboard className="h-5 w-5" />
              Keyboard Shortcuts
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {shortcutGroups.map((group) => (
              <div key={group.title}>
                <h3 className="text-sm font-medium text-muted-foreground mb-2">
                  {group.title}
                </h3>
                <div className="space-y-1.5">
                  {group.shortcuts.map((shortcut) => (
                    <div
                      key={shortcut.key}
                      className="flex items-center justify-between py-1"
                    >
                      <span className="text-sm">{shortcut.description}</span>
                      <ShortcutKey>{shortcut.key}</ShortcutKey>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
