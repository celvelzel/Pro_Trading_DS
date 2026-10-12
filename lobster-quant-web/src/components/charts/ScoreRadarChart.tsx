'use client'

import { memo, useMemo } from 'react'
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface ScoreRadarChartProps {
  scores?: {
    trend: number
    momentum: number
    volume: number
    pattern: number
  }
  loading?: boolean
  className?: string
}

const DEFAULT_SCORES = {
  trend: 75,
  momentum: 60,
  volume: 85,
  pattern: 45,
}

/**
 * ScoreRadarChart - Renders a radar chart for score decomposition.
 *
 * Visualizes Trend, Momentum, Volume, and Pattern scores.
 * Values are on a scale of 0-100.
 */
export const ScoreRadarChart = memo(function ScoreRadarChart({
  scores = DEFAULT_SCORES,
  loading = false,
  className,
}: ScoreRadarChartProps) {

  const data = useMemo(() => [
    { subject: 'Trend', value: scores.trend },
    { subject: 'Momentum', value: scores.momentum },
    { subject: 'Volume', value: scores.volume },
    { subject: 'Pattern', value: scores.pattern },
  ], [scores])

  // Theme-aware colors
  const colors = useMemo(() => ({
    stroke: 'var(--primary)',
    fill: 'var(--primary)',
    grid: 'var(--border)',
    text: 'var(--muted-foreground)',
    tooltipBg: 'var(--popover)',
    tooltipBorder: 'var(--border)',
  }), [])

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Score Decomposition</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <div className="w-full h-full bg-muted/20 animate-pulse rounded-full" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Score Decomposition</CardTitle>
      </CardHeader>
      <CardContent className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
            <PolarGrid stroke={colors.grid} />
            <PolarAngleAxis
              dataKey="subject"
              tick={{ fill: colors.text, fontSize: 12 }}
            />
            <PolarRadiusAxis
              angle={30}
              domain={[0, 100]}
              tick={false}
              axisLine={false}
            />
            <Radar
              name="Score"
              dataKey="value"
              stroke={colors.stroke}
              fill={colors.fill}
              fillOpacity={0.18}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: colors.tooltipBg,
                borderColor: colors.tooltipBorder,
                color: 'var(--popover-foreground)',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              itemStyle={{ color: colors.stroke }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
})
