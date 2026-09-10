import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import PostEventReportPage from './PostEventReportPage'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

vi.mock('../api/client', () => ({ api: { get: vi.fn() } }))
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const REPORT = {
  run_id: 7,
  scenario_name: 'Moderate Flood',
  status: 'completed',
  started_by_name: 'Coordinator One',
  started_at: '2026-09-10T00:00:00Z',
  ended_at: '2026-09-10T01:00:00Z',
  tick_count: 12,
  status_counts: { executed: 1, rejected: 1 },
  recommendations: [
    {
      id: 1, zone_id: 5, zone_name: 'Bellandur', type: 'evacuation_assignment',
      status: 'executed', reason: 'Rising water level', created_at: '2026-09-10T00:05:00Z',
      review: { action: 'approve', reviewed_by_name: 'Zone Admin', reason: null, created_at: '2026-09-10T00:06:00Z' },
    },
    {
      id: 2, zone_id: 6, zone_name: 'Marathahalli', type: 'evacuation_assignment',
      status: 'rejected', reason: 'Minor rainfall', created_at: '2026-09-10T00:07:00Z',
      review: { action: 'reject', reviewed_by_name: 'Zone Admin', reason: 'not warranted', created_at: '2026-09-10T00:08:00Z' },
    },
  ],
  audit_trail: [
    { id: 1, event_type: 'recommendation_approved', entity_type: 'recommendation', entity_id: 1, actor_name: 'Zone Admin', created_at: '2026-09-10T00:06:00Z' },
    { id: 2, event_type: 'recommendation_rejected', entity_type: 'recommendation', entity_id: 2, actor_name: 'Zone Admin', created_at: '2026-09-10T00:08:00Z' },
  ],
}

function renderReport(runId = '7') {
  return render(
    <MemoryRouter initialEntries={[`/report/${runId}`]}>
      <Routes>
        <Route path="/report/:runId" element={<PostEventReportPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('PostEventReportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { id: 1 }, logout: vi.fn() })
  })

  it('fetches the report for the run id in the url', async () => {
    api.get.mockResolvedValue(REPORT)

    renderReport('7')

    await screen.findByText('Moderate Flood')
    expect(api.get).toHaveBeenCalledWith('/reports/7')
  })

  it('renders the run summary and status counts', async () => {
    api.get.mockResolvedValue(REPORT)

    renderReport()

    expect(await screen.findByText('Moderate Flood')).toBeInTheDocument()
    expect(screen.getByText('Coordinator One')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText(/executed: 1/)).toBeInTheDocument()
    expect(screen.getByText(/rejected: 1/)).toBeInTheDocument()
  })

  it('renders each recommendation with its review outcome', async () => {
    api.get.mockResolvedValue(REPORT)

    renderReport()

    expect(await screen.findByText('Bellandur')).toBeInTheDocument()
    expect(screen.getByText(/APPROVE by Zone Admin/)).toBeInTheDocument()
    expect(screen.getByText(/REJECT by Zone Admin.*not warranted/)).toBeInTheDocument()
  })

  it('renders the audit trail', async () => {
    api.get.mockResolvedValue(REPORT)

    renderReport()

    await screen.findByText('Moderate Flood')
    expect(screen.getByText('recommendation_approved')).toBeInTheDocument()
    expect(screen.getByText('recommendation_rejected')).toBeInTheDocument()
  })

  it('shows a message when there are no recommendations', async () => {
    api.get.mockResolvedValue({ ...REPORT, recommendations: [], status_counts: {} })

    renderReport()

    expect(await screen.findByText(/No recommendations to show/)).toBeInTheDocument()
    expect(screen.getByText(/No recommendations were generated/)).toBeInTheDocument()
  })

  it('surfaces an error when the report fails to load', async () => {
    api.get.mockRejectedValue(new Error('Simulation run not found'))

    renderReport('999')

    expect(await screen.findByText(/ERROR: Simulation run not found/)).toBeInTheDocument()
  })
})
