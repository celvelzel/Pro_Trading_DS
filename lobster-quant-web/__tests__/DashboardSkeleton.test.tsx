/**
 * Unit tests for DashboardSkeleton component.
 * Verifies the skeleton loader renders the expected structure.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { DashboardSkeleton } from '@/components/skeletons/DashboardSkeleton'

describe('DashboardSkeleton', () => {
  it('renders without crashing', () => {
    const { container } = render(<DashboardSkeleton />)
    expect(container.firstChild).toBeTruthy()
  })

  it('renders as a div container', () => {
    const { container } = render(<DashboardSkeleton />)
    expect(container.firstChild?.nodeName).toBe('DIV')
  })

  it('contains skeleton elements', () => {
    const { container } = render(<DashboardSkeleton />)
    // Should have multiple skeleton elements with height classes
    const skeletons = container.querySelectorAll('[class*="h-"]')
    expect(skeletons.length).toBeGreaterThan(10)
  })

  it('contains card elements', () => {
    const { container } = render(<DashboardSkeleton />)
    // Should have card elements for status, info, chart, etc.
    const cards = container.querySelectorAll('[class*="rounded"]')
    expect(cards.length).toBeGreaterThan(0)
  })

  it('contains animation classes', () => {
    const { container } = render(<DashboardSkeleton />)
    const animatedElements = container.querySelectorAll('[class*="animate-in"]')
    expect(animatedElements.length).toBeGreaterThan(0)
  })

  it('has proper layout structure', () => {
    const { container } = render(<DashboardSkeleton />)
    // Should have a main container with padding
    const mainDiv = container.firstChild as HTMLElement
    expect(mainDiv.className).toContain('p-4')
    expect(mainDiv.className).toContain('space-y-6')
  })
})
