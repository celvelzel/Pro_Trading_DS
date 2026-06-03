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
import { useTheme } from 'next-themes'
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
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const data = useMemo(() => [
    { subject: 'Trend', value: scores.trend },
    { subject: 'Momentum', value: scores.momentum },
    { subject: 'Volume', value: scores.volume },
    { subject: 'Pattern', value: scores.pattern },
  ], [scores])

  // Theme-aware colors
  const colors = useMemo(() => ({
    stroke: isDark ? '#8ab4f8' : '#1A73E8',
    fill: isDark ? '#8ab4f8' : '#1A73E8',
    grid: isDark ? '#333333' : '#E5E7EB',
    text: isDark ? '#9AA0A6' : '#5F6368',
    tooltipBg: isDark ? '#2D2E31' : '#FFFFFF',
    tooltipBorder: isDark ? '#3C4043' : '#E5E7EB',
  }), [isDark])

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
              fillOpacity={0.5}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: colors.tooltipBg,
                borderColor: colors.tooltipBorder,
                color: isDark ? '#E8EAED' : '#202124',
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
