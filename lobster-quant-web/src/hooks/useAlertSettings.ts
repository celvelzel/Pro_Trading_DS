'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import type { AlertRuleSettings, AlertSettingsMap } from '@/lib/types'

// ============================================================================
// Constants
// ============================================================================

const STORAGE_KEY = 'lobster-quant-alert-settings'
const DEFAULT_COOLDOWN_MINUTES = 5

// ============================================================================
// localStorage Helpers
// ============================================================================

function loadSettings(): AlertSettingsMap {
  if (typeof window === 'undefined') return {}
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveSettings(map: AlertSettingsMap): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map))
  } catch {
    // localStorage may be full or unavailable
  }
}

// ============================================================================
// Hook: Alert Settings (per-rule sound & cooldown)
// ============================================================================

/**
 * Manages per-rule alert settings (sound toggle, cooldown period) with
 * localStorage persistence and in-memory cooldown tracking.
 */
export function useAlertSettings() {
  const [settingsMap, setSettingsMap] = useState<AlertSettingsMap>(loadSettings)

  // Cooldown tracking: ruleId → last triggered timestamp (ms)
  const cooldownRef = useRef<Map<string, number>>(new Map())

  // Persist to localStorage on change
  useEffect(() => {
    saveSettings(settingsMap)
  }, [settingsMap])

  /** Get settings for a specific rule (returns defaults if not set). */
  const getRuleSettings = useCallback(
    (ruleId: string): AlertRuleSettings => {
      return settingsMap[ruleId] ?? {
        soundEnabled: true,
        cooldownMinutes: DEFAULT_COOLDOWN_MINUTES,
      }
    },
    [settingsMap]
  )

  /** Update settings for a specific rule. */
  const updateRuleSettings = useCallback(
    (ruleId: string, patch: Partial<AlertRuleSettings>) => {
      setSettingsMap((prev) => {
        const current = prev[ruleId] ?? {
          soundEnabled: true,
          cooldownMinutes: DEFAULT_COOLDOWN_MINUTES,
        }
        return { ...prev, [ruleId]: { ...current, ...patch } }
      })
    },
    []
  )

  /**
   * Check if a rule is currently in cooldown.
   * Returns true if the rule should be suppressed (still cooling down).
   */
  const isInCooldown = useCallback(
    (ruleId: string, cooldownMinutes: number): boolean => {
      const lastTriggered = cooldownRef.current.get(ruleId)
      if (lastTriggered === undefined) return false
      const elapsed = Date.now() - lastTriggered
      return elapsed < cooldownMinutes * 60 * 1000
    },
    []
  )

  /** Mark a rule as just triggered (starts cooldown timer). */
  const markTriggered = useCallback((ruleId: string): void => {
    cooldownRef.current.set(ruleId, Date.now())
  }, [])

  /** Get remaining cooldown seconds for a rule (0 if not in cooldown). */
  const getCooldownRemaining = useCallback(
    (ruleId: string, cooldownMinutes: number): number => {
      const lastTriggered = cooldownRef.current.get(ruleId)
      if (lastTriggered === undefined) return 0
      const elapsed = Date.now() - lastTriggered
      const cooldownMs = cooldownMinutes * 60 * 1000
      if (elapsed >= cooldownMs) return 0
      return Math.ceil((cooldownMs - elapsed) / 1000)
    },
    []
  )

  return {
    settingsMap,
    getRuleSettings,
    updateRuleSettings,
    isInCooldown,
    markTriggered,
    getCooldownRemaining,
  }
}
