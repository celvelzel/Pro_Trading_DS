'use client'

import { useRef } from 'react'
import { useSettingsContext } from '../settings-context'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Download, Upload, RotateCcw, FileJson } from 'lucide-react'

export default function ImportExportPage() {
  const {
    handleExport,
    handleImport,
    handleFileChange,
    handleReset,
    fileInputRef,
  } = useSettingsContext()

  return (
    <div className="space-y-6">
      {/* Export */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="w-5 h-5" />
            Export Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-text-secondary">
            Download your current settings as a JSON file. This is useful for backing up your
            configuration or sharing it across devices.
          </p>
          <Button onClick={handleExport} variant="outline">
            <Download className="w-4 h-4 mr-2" />
            Export as JSON
          </Button>
        </CardContent>
      </Card>

      {/* Import */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Import Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-text-secondary">
            Import settings from a previously exported JSON file. This will overwrite your current
            settings. You will be asked to confirm before the import is applied.
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button onClick={handleImport} variant="outline">
            <Upload className="w-4 h-4 mr-2" />
            Import from JSON
          </Button>
        </CardContent>
      </Card>

      {/* Reset */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RotateCcw className="w-5 h-5" />
            Reset Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-text-secondary">
            Reset all settings to their default values. This action will fetch fresh defaults from
            the server if available, otherwise local defaults will be used.
          </p>
          <Button onClick={handleReset} variant="destructive">
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset to Defaults
          </Button>
        </CardContent>
      </Card>

      {/* File Format Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileJson className="w-5 h-5" />
            File Format
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-secondary mb-3">
            Settings files use JSON format with the following structure:
          </p>
          <pre className="p-4 bg-muted rounded-md text-xs overflow-x-auto">
{`{
  "markets": { "enableUS": true, ... },
  "data": { "dataYears": 3, ... },
  "scoring": { "trend": 0.3, ... },
  "backtest": { "holdingDays": 20, ... },
  "offFilter": { "vixThreshold": 35, ... },
  "indicators": { "maShortPeriod": 20, ... }
}`}
          </pre>
        </CardContent>
      </Card>
    </div>
  )
}
