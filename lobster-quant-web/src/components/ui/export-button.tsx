'use client'

import { memo, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Download } from 'lucide-react'
import type { ComponentProps } from 'react'

// ============================================================================
// CSV Utilities
// ============================================================================

/** Escape a single CSV cell value. Handles commas, quotes, and newlines. */
function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n') || value.includes('\r')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

/** Trigger a browser CSV download. */
function downloadFile(csv: string, filename: string) {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// ============================================================================
// Types
// ============================================================================

export interface ColumnDef {
  /** Object key to read from each row */
  key: string
  /** CSV header label */
  header: string
  /** Optional formatter – receives the raw cell value and the full row */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  format?: (...args: any[]) => string
}

interface ExportButtonProps {
  /** Data rows to export */
  data: unknown[]
  /** Column definitions (keys + headers + optional formatters) */
  columns: ColumnDef[]
  /** CSV filename (without .csv extension) */
  filename: string
}

// ============================================================================
// Component
// ============================================================================

export const ExportButton = memo(function ExportButton({
  data,
  columns,
  filename,
  disabled,
  ...buttonProps
}: ExportButtonProps & Omit<ComponentProps<typeof Button>, 'children'>) {
  const handleClick = useCallback(() => {
    const headers = columns.map((c) => escapeCSV(c.header))
    const rows = data.map((row) => {
      const obj = row as Record<string, unknown>
      return columns
        .map((c) => {
          const raw = c.format
            ? c.format(obj[c.key], obj)
            : String(obj[c.key] ?? '')
          return escapeCSV(raw)
        })
        .join(',')
    })
    const csv = [headers.join(','), ...rows].join('\r\n')
    const timestamp = new Date().toISOString().slice(0, 10)
    downloadFile(csv, `${filename}-${timestamp}.csv`)
  }, [data, columns, filename])

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleClick}
      disabled={disabled || data.length === 0}
      {...buttonProps}
    >
      <Download className="h-4 w-4 mr-1" />
      Export CSV
    </Button>
  )
})
