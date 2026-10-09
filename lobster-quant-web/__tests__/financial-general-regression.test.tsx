import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { it, expect, vi } from 'vitest'
import CopilotPage from '@/app/copilot/page'
import { agentApi } from '@/lib/agent-api'
vi.mock('next/navigation', () => ({ useSearchParams: () => new URLSearchParams() }))
vi.mock('@/hooks/useAgentRun', () => ({ useAgentRun: () => ({ run: null, setRun: vi.fn(), loading: false, error: null, refresh: vi.fn() }) }))
vi.mock('@/hooks/useAgentEvents', () => ({ useAgentEvents: () => ({ events: [] }) }))
vi.mock('@/components/copilot/MemoryPanel', () => ({ MemoryPanel: () => null }))
vi.mock('@/lib/agent-api', async original => ({ ...await original<typeof import('@/lib/agent-api')>(), agentApi: { createConversation: vi.fn().mockResolvedValue({ id: 'legacy-c' }), createRun: vi.fn().mockResolvedValue({ id: 'legacy-r' }) } }))
it('defaults to General and preserves unchanged goal/mode legacy createRun', async () => {
  render(<CopilotPage />)
  expect(screen.getByRole('combobox', { name: 'Workflow' })).toHaveValue('general')
  fireEvent.change(screen.getByLabelText('研究目标'), { target: { value: 'legacy goal' } })
  fireEvent.click(screen.getByRole('button', { name: '开始规划' }))
  await waitFor(() => expect(agentApi.createRun).toHaveBeenCalledWith('legacy-c', 'legacy goal', 'review'))
})
