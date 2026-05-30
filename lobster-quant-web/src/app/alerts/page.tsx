'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  useAlertRules,
  useCreateAlertRule,
  useDeleteAlertRule,
  useToggleAlertRule,
  useTriggeredAlerts,
  useMarkAlertsRead,
} from '@/hooks/useAlerts'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import {
  Bell,
  BellRing,
  Plus,
  Trash2,
  Loader2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  RefreshCw,
} from 'lucide-react'
import type { AlertCondition, AlertRule, TriggeredAlert } from '@/lib/types'

// ============================================================================
// Browser Notification Helper
// ============================================================================

function requestNotificationPermission(): void {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }
}

function showBrowserNotification(title: string, body: string): void {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, {
      body,
      icon: '/favicon.ico',
      tag: 'lobster-quant-alert',
    })
  }
}

// ============================================================================
// Condition Display Helpers
// ============================================================================

const CONDITION_LABELS: Record<AlertCondition, string> = {
  score_above: 'Score Above',
  score_below: 'Score Below',
  price_above: 'Price Above',
  price_below: 'Price Below',
  signal_change: 'Signal Change',
}

const CONDITION_ICONS: Record<AlertCondition, typeof TrendingUp> = {
  score_above: TrendingUp,
  score_below: TrendingDown,
  price_above: DollarSign,
  price_below: DollarSign,
  signal_change: Activity,
}

function formatThreshold(condition: AlertCondition, threshold: number): string {
  if (condition.startsWith('price_')) {
    return `$${threshold.toFixed(2)}`
  }
  if (condition === 'signal_change') {
    const signalMap: Record<number, string> = { 1: 'Bullish', 0: 'Neutral', '-1': 'Bearish' }
    return signalMap[threshold] ?? threshold.toString()
  }
  return threshold.toFixed(1)
}

function formatCurrentValue(condition: AlertCondition, value: number): string {
  if (condition.startsWith('price_')) {
    return `$${value.toFixed(2)}`
  }
  return value.toFixed(1)
}

// ============================================================================
// Alert Rule Form
// ============================================================================

function AlertRuleForm({ onSuccess }: { onSuccess?: () => void }) {
  const [symbol, setSymbol] = useState('')
  const [condition, setCondition] = useState<AlertCondition>('score_above')
  const [threshold, setThreshold] = useState('')
  const createMutation = useCreateAlertRule()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!symbol.trim() || !threshold) return

    createMutation.mutate(
      {
        symbol: symbol.trim().toUpperCase(),
        condition,
        threshold: parseFloat(threshold),
      },
      {
        onSuccess: () => {
          setSymbol('')
          setThreshold('')
          onSuccess?.()
        },
      }
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Plus className="h-5 w-5 text-primary" />
          <CardTitle>Create Alert Rule</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Symbol */}
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Stock Symbol
              </label>
              <Input
                placeholder="e.g. AAPL"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                required
              />
            </div>

            {/* Condition */}
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Condition
              </label>
              <Select value={condition} onValueChange={(v) => setCondition(v as AlertCondition)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="score_above">Score Above</SelectItem>
                  <SelectItem value="score_below">Score Below</SelectItem>
                  <SelectItem value="price_above">Price Above</SelectItem>
                  <SelectItem value="price_below">Price Below</SelectItem>
                  <SelectItem value="signal_change">Signal Change</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Threshold */}
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Threshold
              </label>
              <Input
                type="number"
                step="any"
                placeholder={condition.startsWith('price_') ? '150.00' : '70.0'}
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                required
              />
            </div>
          </div>

          <Button
            type="submit"
            disabled={createMutation.isPending || !symbol.trim() || !threshold}
          >
            {createMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Plus className="h-4 w-4 mr-2" />
            )}
            Create Alert
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Alert Rule Item
// ============================================================================

function AlertRuleItem({
  rule,
  onDelete,
  onToggle,
}: {
  rule: AlertRule
  onDelete: (id: string) => void
  onToggle: (id: string, enabled: boolean) => void
}) {
  const deleteMutation = useDeleteAlertRule()
  const toggleMutation = useToggleAlertRule()
  const Icon = CONDITION_ICONS[rule.condition]

  return (
    <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${rule.enabled ? 'bg-primary/10' : 'bg-muted'}`}>
          <Icon className={`h-4 w-4 ${rule.enabled ? 'text-primary' : 'text-muted-foreground'}`} />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium">{rule.symbol}</span>
            <Badge variant="outline" className="text-xs">
              {CONDITION_LABELS[rule.condition]}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {formatThreshold(rule.condition, rule.threshold)}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Created {new Date(rule.createdAt).toLocaleDateString()}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          checked={rule.enabled}
          onCheckedChange={(checked) => {
            toggleMutation.mutate({ ruleId: rule.id, enabled: checked })
            onToggle(rule.id, checked)
          }}
          disabled={toggleMutation.isPending}
        />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => {
            deleteMutation.mutate(rule.id)
            onDelete(rule.id)
          }}
          disabled={deleteMutation.isPending}
          className="text-destructive hover:text-destructive"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

// ============================================================================
// Triggered Alert Item
// ============================================================================

function TriggeredAlertItem({ alert }: { alert: TriggeredAlert }) {
  const Icon = CONDITION_ICONS[alert.condition]

  return (
    <div
      className={`flex items-start gap-3 p-4 border rounded-lg transition-colors ${
        alert.read ? 'bg-background' : 'bg-primary/5 border-primary/20'
      }`}
    >
      <div className={`p-2 rounded-lg ${alert.read ? 'bg-muted' : 'bg-warning/10'}`}>
        {alert.read ? (
          <Icon className="h-4 w-4 text-muted-foreground" />
        ) : (
          <BellRing className="h-4 w-4 text-warning" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium">{alert.symbol}</span>
          <Badge variant={alert.read ? 'outline' : 'default'} className="text-xs">
            {CONDITION_LABELS[alert.condition]}
          </Badge>
        </div>
        <p className="text-sm text-text-secondary mt-1">{alert.message}</p>
        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
          <span>
            Threshold: {formatThreshold(alert.condition, alert.threshold)}
          </span>
          <span>
            Current: {formatCurrentValue(alert.condition, alert.currentValue)}
          </span>
          <span>{new Date(alert.triggeredAt).toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Main Page
// ============================================================================

export default function AlertsPage() {
  const { data: rulesData, isLoading: rulesLoading, error: rulesError } = useAlertRules()
  const { data: triggeredData, isLoading: triggeredLoading } = useTriggeredAlerts()
  const markReadMutation = useMarkAlertsRead()

  const rules = rulesData?.rules ?? []
  const triggeredAlerts = triggeredData?.alerts ?? []
  const unreadCount = triggeredData?.unreadCount ?? 0

  // Track previous unread count for browser notifications
  const [prevUnreadCount, setPrevUnreadCount] = useState(0)

  // Request notification permission on mount
  useEffect(() => {
    requestNotificationPermission()
  }, [])

  // Show browser notification when new alerts arrive
  useEffect(() => {
    if (unreadCount > prevUnreadCount && prevUnreadCount > 0) {
      const newAlerts = triggeredAlerts.filter((a) => !a.read).slice(0, 3)
      const body = newAlerts.map((a) => a.message).join('\n')
      showBrowserNotification(
        `${unreadCount - prevUnreadCount} New Alert(s)`,
        body
      )
    }
    setPrevUnreadCount(unreadCount)
  }, [unreadCount, triggeredAlerts, prevUnreadCount])

  const handleMarkAllRead = useCallback(() => {
    markReadMutation.mutate()
  }, [markReadMutation])

  if (rulesError) {
    return (
      <div className="p-6">
        <ErrorState
          title="Failed to load alerts"
          message={rulesError.message}
        />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold text-text-primary">Alerts</h1>
            {unreadCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                {unreadCount} unread
              </Badge>
            )}
          </div>
          <p className="text-text-secondary mt-1">
            Set up alerts for stock prices, scores, and signal changes
          </p>
        </div>
        {unreadCount > 0 && (
          <Button variant="outline" onClick={handleMarkAllRead} disabled={markReadMutation.isPending}>
            <Bell className="h-4 w-4 mr-2" />
            Mark All Read
          </Button>
        )}
      </div>

      {/* Create Alert Form */}
      <AlertRuleForm />

      {/* Alert Rules List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Alert Rules</CardTitle>
            <Badge variant="outline">{rules.length} rules</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {rulesLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : rules.length === 0 ? (
            <EmptyState
              icon="inbox"
              title="No alert rules"
              message="Create your first alert rule above to get notified when conditions are met."
            />
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <AlertRuleItem
                  key={rule.id}
                  rule={rule}
                  onDelete={() => {}}
                  onToggle={() => {}}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Triggered Alerts History */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle>Alert History</CardTitle>
              <RefreshCw
                className={`h-4 w-4 text-muted-foreground ${triggeredLoading ? 'animate-spin' : ''}`}
              />
            </div>
            <Badge variant="outline">{triggeredAlerts.length} alerts</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {triggeredLoading && triggeredAlerts.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : triggeredAlerts.length === 0 ? (
            <EmptyState
              icon="inbox"
              title="No triggered alerts"
              message="Alerts will appear here when your conditions are met. The system checks every 60 seconds."
            />
          ) : (
            <div className="space-y-2">
              {triggeredAlerts.map((alert) => (
                <TriggeredAlertItem key={alert.id} alert={alert} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
