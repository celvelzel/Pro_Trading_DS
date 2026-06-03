'use client'

import { type ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { SettingsProvider, useSettingsContext } from './settings-context'
import { Button } from '@/components/ui/button'
import { HelpTooltip } from '@/components/ui/help-tooltip'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import {
  Settings,
  Save,
  RotateCcw,
  Database,
  BarChart3,
  FlaskConical,
  ShieldAlert,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Download,
  Upload,
} from 'lucide-react'

// ============================================================================
// Navigation Items
// ============================================================================

const NAV_ITEMS = [
  { href: '/settings/scoring', label: 'Scoring', icon: BarChart3 },
  { href: '/settings/data', label: 'Data & Markets', icon: Database },
  { href: '/settings/backtest', label: 'Backtest', icon: FlaskConical },
  { href: '/settings/off-filter', label: 'OFF Filter', icon: ShieldAlert },
  { href: '/settings/import-export', label: 'Import / Export', icon: Download },
] as const

// ============================================================================
// Inner Layout (uses context)
// ============================================================================

function SettingsLayoutInner({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const {
    saveStatus,
    errorMessage,
    isLoadingSettings,
    handleSave,
    handleReset,
    handleExport,
    handleImport,
    handleFileChange,
    handleConfirmImport,
    importConfirmOpen,
    setImportConfirmOpen,
    fileInputRef,
    setPendingImport,
  } = useSettingsContext()

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary flex items-center gap-2">
            <Settings className="w-8 h-8" />
            Settings
            <HelpTooltip helpKey="settings.title" />
          </h1>
          <p className="text-text-secondary mt-1">
            Configure your trading analysis preferences
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isLoadingSettings && (
            <span className="text-sm text-text-secondary flex items-center gap-1">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading...
            </span>
          )}
          {saveStatus === 'saved' && (
            <span className="text-sm text-success flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4" />
              Saved!
            </span>
          )}
          {saveStatus === 'error' && errorMessage && (
            <span className="text-sm text-destructive flex items-center gap-1">
              <AlertCircle className="w-4 h-4" />
              {errorMessage}
            </span>
          )}
          <Button variant="outline" onClick={handleReset} disabled={false}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button variant="outline" onClick={handleImport}>
            <Upload className="w-4 h-4 mr-2" />
            Import
          </Button>
          <Button variant="outline" onClick={handleExport}>
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Button onClick={handleSave} disabled={saveStatus === 'saving' || isLoadingSettings}>
            {saveStatus === 'saving' ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Settings
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Content with sidebar */}
      <div className="flex gap-6">
        {/* Sidebar Navigation */}
        <nav className="w-56 shrink-0">
          <ul className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
              const Icon = item.icon
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-accent text-accent-foreground'
                        : 'text-text-secondary hover:text-text-primary hover:bg-accent/50'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          {children}
        </div>
      </div>

      {/* Import Confirmation Dialog */}
      <AlertDialog open={importConfirmOpen} onOpenChange={setImportConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Import Settings</AlertDialogTitle>
            <AlertDialogDescription>
              This will overwrite your current settings with the imported values.
              You can save to the server afterwards if needed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setPendingImport(null)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmImport}>
              Import
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

// ============================================================================
// Outer Layout (provides context)
// ============================================================================

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <SettingsProvider>
      <SettingsLayoutInner>{children}</SettingsLayoutInner>
    </SettingsProvider>
  )
}
