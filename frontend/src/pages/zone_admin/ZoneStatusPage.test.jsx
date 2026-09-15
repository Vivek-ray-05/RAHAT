import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import ZoneStatusPage from './ZoneStatusPage'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'

vi.mock('../../api/client', () => ({ api: { get: vi.fn() } }))
vi.mock('../../context/AuthContext', () => ({ useAuth: vi.fn() }))

const ZONE = {
  id: 5, name: 'Bellandur', population: 11736, elevation_tier: 'low',
  hospital_count: 3, flood_risk_base: 9.6, data_quality_json: {},
}

describe('ZoneStatusPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows a message when the account has no zone assignment', async () => {
    useAuth.mockReturnValue({ user: { id: 1, zone_id: null } })

    render(<ZoneStatusPage />)

    expect(await screen.findByText(/no zone assignment/i)).toBeInTheDocument()
  })

  it('renders the zone status and its citizen reports, SOS flagged', async () => {
    useAuth.mockReturnValue({ user: { id: 2, zone_id: 5 } })
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([ZONE])
      if (path.startsWith('/citizen-reports')) {
        return Promise.resolve([{ id: 1, description: 'Water rising', is_sos: true }])
      }
      return Promise.resolve([])
    })

    render(<ZoneStatusPage />)

    expect(await screen.findByText('Bellandur')).toBeInTheDocument()
    expect(screen.getByText('9.6')).toBeInTheDocument()
    expect(screen.getByText(/Water rising/)).toBeInTheDocument()
    expect(screen.getByText('[SOS]')).toBeInTheDocument()
  })
})
