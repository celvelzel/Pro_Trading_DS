'use client'

import { type ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { SettingsProvider, useSettingsContext } from './settings-context'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/layout/PageHeader'
import { HelpTooltip } from '@/components/ui/help-tooltip'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import {
  Save,
  Database,
  RotateCcw,
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
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      {/* Page Header */}
      <PageHeader title="Settings" description="Configure your trading analysis preferences" actions={
        <div className="flex flex-wrap items-center gap-2">
          <HelpTooltip helpKey="settings.title" />
          {isLoadingSettings && (
            <span className="text-sm text-muted-foreground flex items-center gap-1">
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
      } />

      {/* Content with sidebar */}
      <div className="flex min-w-0 flex-col gap-6 lg:flex-row">
        {/* Sidebar Navigation */}
        <nav aria-label="Settings sections" className="min-w-0 lg:w-48 lg:shrink-0">
          <ul className="flex flex-wrap gap-1 lg:flex-col">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
              const Icon = item.icon
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex min-h-10 items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-accent text-accent-foreground'
                        : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
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
