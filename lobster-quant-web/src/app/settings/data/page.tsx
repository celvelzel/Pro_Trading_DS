'use client'

import { useSettingsStore } from '@/stores/settingsStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { sliderVal } from '../settings-context'

export default function DataSettingsPage() {
  const { enableUS, enableHK, enableA, dataYears, cacheTTL, setMarkets, setDataSettings } = useSettingsStore()
  return <div className="space-y-6">
    <Card><CardHeader><CardTitle className="text-sm font-semibold">Markets</CardTitle></CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-3">{([
        ['enableUS', 'US stocks', enableUS], ['enableHK', 'Hong Kong stocks', enableHK], ['enableA', 'A-shares', enableA],
      ] as const).map(([key, label, enabled]) => <label key={key} className="flex min-h-12 items-center justify-between gap-4 rounded-md border border-border p-3 text-sm">
        {label}<Switch checked={enabled} onCheckedChange={value => setMarkets({ [key]: value })} aria-label={label} />
      </label>)}</CardContent>
    </Card>
    <Card><CardHeader><CardTitle className="text-sm font-semibold">Data & Cache</CardTitle></CardHeader>
      <CardContent className="grid gap-6 sm:grid-cols-2">
        <div className="space-y-3"><label id="data-years-label" className="text-sm font-medium">Historical data: <span className="font-mono">{dataYears} years</span></label>
          <Slider aria-labelledby="data-years-label" value={[dataYears]} onValueChange={v => setDataSettings({ dataYears: sliderVal(v) })} min={1} max={10} step={1} />
          <p className="text-xs text-muted-foreground">History requested for market analysis.</p></div>
        <div className="space-y-3"><label id="cache-ttl-label" className="text-sm font-medium">Cache lifetime: <span className="font-mono">{cacheTTL} seconds</span></label>
          <Slider aria-labelledby="cache-ttl-label" value={[cacheTTL]} onValueChange={v => setDataSettings({ cacheTTL: sliderVal(v) })} min={60} max={86400} step={60} />
          <p className="text-xs text-muted-foreground">Save Settings applies these preferences to the server.</p></div>
      </CardContent>
    </Card>
  </div>
}
