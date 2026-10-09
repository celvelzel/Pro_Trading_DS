import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { MarketArtifact, PortfolioArtifact } from '@/types/financial-artifacts'
import { MarketResult } from './MarketResult'
import { PortfolioResult } from './PortfolioResult'
import { formatFact, formatValue } from './result-shared'
afterEach(cleanup)
const market: MarketArtifact = { schema_version: 1, producing_run_id: 'run-market-actual', symbol: 'MU', as_of: '2026-10-08T00:00:00Z', status: 'partial', numeric_facts: [{ name: 'market.return_pct', value: 100, unit: 'percentage_points', evidence_id: 'e1', tool_result_id: 't1' }], hypotheses: [{ explanation: 'Company event association', support_ids: ['e1'], against_ids: ['e2'], disposition: 'supported' }], evidence: [{ id: 'e1', source_type: 'news', source_locator: 'javascript:alert(1)', published_at: null, available_at: null, observed_at: '2026-10-07T00:00:00Z', content_hash: 'hash1', excerpt: '<script>alert(1)</script>' }, { id: 'e2', source_type: 'filing', source_locator: 'https://example.com/filing', published_at: '2026-10-06T00:00:00Z', available_at: '2026-10-07T00:00:00Z', observed_at: '2026-10-07T00:00:00Z', content_hash: 'hash2', excerpt: 'counter evidence' }], limitations: ['sector data missing'] }
const portfolio: PortfolioArtifact = { schema_version: 1, producing_run_id: 'run-portfolio-actual', snapshot_id: 'demo-sounding-name', as_of: market.as_of, current_weights: { MU: 0.8, CASH: 0.2 }, proposed_weights: {}, constraint_check: { status: 'unknown', violations: [], unknowns: ['missing classification'] }, risk_comparison: { before: { volatility: 0.25, maximum_drawdown: -0.1, concentration: 0.8, cash_weight: 0.2, tool_result_id: 'risk-before' }, after: { volatility: null, maximum_drawdown: null, concentration: null, cash_weight: null, tool_result_id: 'risk-after' } }, simulation: { tool_result_id: 'simulation-actual', adjustment: 'adjusted', rebalance_cadence: '1 common trading observation', fees_bps: 12, slippage_bps: 5, net_return: 0.05, assumptions: ['initial_purchase_cost_included'] }, evidence_ids: ['ref1'], limitations: ['insufficient history'], status: 'insufficient_data' }
describe('financial results', () => {
  it.each([
    [1e-7, '1E-5%'], [-1e-7, '-1E-5%'],
    [1e-12, '1E-10%'], [-1e-12, '-1E-10%'],
    [Number.MIN_VALUE, '4.94E-322%'], [-Number.MIN_VALUE, '-4.94E-322%'],
    [0, '0%'], [-0, '0%'], [0.123456, '12.3456%'], [-0.123456, '-12.3456%'],
    [1e-6, '0.0001%'], [-1e-6, '-0.0001%'],
  ])('preserves the magnitude and sign of ratio %s', (value, expected) => {
    expect(formatValue(value, 'ratio')).toBe(expected)
  })
  it.each([1, -1])('shows tiny %s-signed weights, risk and simulation returns as nonzero', sign => {
    const tiny = sign * 1e-7
    const expected = sign > 0 ? '1E-5%' : '-1E-5%'
    render(<PortfolioResult artifact={{ ...portfolio,
      current_weights: { MU: tiny }, proposed_weights: { MU: tiny },
      risk_comparison: { before: { ...portfolio.risk_comparison!.before, volatility: tiny }, after: { ...portfolio.risk_comparison!.after, maximum_drawdown: tiny } },
      simulation: { ...portfolio.simulation!, net_return: tiny },
    }} />)
    expect(screen.getByRole('row', { name: `MU ${expected} ${expected}` })).toBeInTheDocument()
    expect(screen.getByRole('row', { name: `年化波动率 ${expected} 未知` })).toBeInTheDocument()
    expect(screen.getByRole('row', { name: `最大回撤 -10% ${expected}` })).toBeInTheDocument()
    expect(screen.getByText(`净收益：${expected}`)).toBeInTheDocument()
  })
  it('formats ratios, percentage values, points and missing values once', () => {
    expect(formatFact({ ...market.numeric_facts[0], name: 'market.volume_ratio_20', value: 3, unit: 'ratio' })).toBe('3 ×')
    expect(formatFact({ ...market.numeric_facts[0], name: 'sector.relative_strength', value: -0.05, unit: 'ratio' })).toBe('-0.05 ratio（原始比例）')
    expect(formatValue(0.12, 'ratio')).toBe('12%')
    expect(formatValue(12, 'percent')).toBe('12%')
    expect(formatValue(12, 'percentage_points')).toBe('12 个百分点')
    expect(formatValue(0, 'ratio')).toBe('0%')
    expect(formatValue(1, 'ratio')).toBe('100%')
    expect(formatValue(null, 'ratio')).toBe('未知')
    expect(formatValue(undefined)).toBe('未知')
    expect(formatValue(Number.NaN)).toBe('未知')
    expect(formatValue(Number.POSITIVE_INFINITY)).toBe('未知')
  })
  it('renders partial facts and escaped sources without inferring real data', () => {
    const { container } = render(<MarketResult artifact={market} />)
    expect(screen.getByText('100 个百分点')).toBeInTheDocument()
    expect(screen.getByText(/部分结果/)).toBeInTheDocument()
    expect(screen.getByText(/来源类型未知/)).toBeInTheDocument()
    expect(screen.getByText(/不能确认因果关系/)).toBeInTheDocument()
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('a[href^="javascript:"]')).toBeNull()
    expect(screen.getByText('javascript:alert(1)')).toBeInTheDocument()
    expect(screen.getByText(/<script>alert/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'https://example.com/filing', hidden: true })).toHaveAttribute('rel', 'noopener noreferrer')
    expect(screen.getByText(/run-market-actual/)).toBeInTheDocument()
    expect(container.querySelector('caption')).not.toBeNull()
    expect(container.querySelector('th[scope="row"]')).not.toBeNull()
  })
  it('states demo ownership and insufficient evidence explicitly', () => {
    render(<MarketResult artifact={{ ...market, status: 'insufficient_evidence', numeric_facts: [], hypotheses: [], evidence: [] }} sourceProfile="demo" />)
    expect(screen.getByText(/不是你的持仓\/行情/)).toBeInTheDocument()
    expect(screen.getByText(/证据不足/)).toBeInTheDocument()
    expect(screen.getByText('暂无数值事实。')).toBeInTheDocument()
  })
  it('retains unknown weights/risk and actual simulation units and assumptions', () => {
    render(<PortfolioResult artifact={portfolio} />)
    expect(screen.getAllByText('未知').length).toBe(6)
    expect(screen.getByText('25%')).toBeInTheDocument()
    expect(screen.getByText('-10%')).toBeInTheDocument()
    expect(screen.getByText('净收益：5%')).toBeInTheDocument()
    expect(screen.getByText(/12 bps/)).toBeInTheDocument()
    expect(screen.getByText(/不是收益预测/)).toBeInTheDocument()
    expect(screen.getByText('initial_purchase_cost_included')).toBeInTheDocument()
    expect(screen.getByText(/run-portfolio-actual/)).toBeInTheDocument()
    expect(screen.getByText(/未提供证据详情：ref1/)).toBeInTheDocument()
    expect(screen.getByText(/来源类型未知/)).toBeInTheDocument()
  })
  it('shows infeasibility and violations with null limits without implying zero', () => {
    render(<PortfolioResult artifact={{ ...portfolio, status: 'infeasible', risk_comparison: null, simulation: null, constraint_check: { status: 'fail', unknowns: [], violations: [{ constraint: 'capacity', symbol: null, actual: null, limit: null, reason: 'insufficient capacity' }] } }} />)
    expect(screen.getByText(/不可行/)).toBeInTheDocument()
    expect(screen.getByText(/实际值：未知 · 限值：未知/)).toBeInTheDocument()
    expect(screen.getByText('暂无可用历史模拟。')).toBeInTheDocument()
  })
  it('renders empty, loading and error results', () => {
    const { rerender } = render(<MarketResult />)
    expect(screen.getByRole('status')).toHaveTextContent('暂无结果')
    rerender(<PortfolioResult loading />)
    expect(screen.getByRole('status')).toHaveTextContent('正在加载')
    rerender(<PortfolioResult error="network failed" />)
    expect(screen.getByRole('alert')).toHaveTextContent('network failed')
  })
})
