import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import RoutePlanningPage from './RoutePlanningPage'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { useSocket } from '../../context/SocketContext'

vi.mock('../../api/client', () => ({ api: { get: vi.fn(), post: vi.fn() } }))
vi.mock('../../context/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../../context/SocketContext', () => ({ useSocket: vi.fn() }))

const ZONE = { id: 5, name: 'Bellandur', center_lat: 12.9304, center_lon: 77.6784, flood_risk_base: 9.6 }
const REC = {
  id: 42, status: 'pending_review',
  payload_json: { zone_id: 5, zone_name: 'Bellandur', priority_score: 0.9, risk_score: 8.1, reason: 'Rising water', assigned_shelter_id: null, assigned_population: 0 },
}

describe('RoutePlanningPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { id: 1, zone_id: 5 } })
    useSocket.mockReturnValue({ latestTick: null })
  })

  it('renders the zone admin their own zone recommendation', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/recommendations') return Promise.resolve([REC])
      if (path === '/shelters') return Promise.resolve([])
      if (path === '/zones') return Promise.resolve([ZONE])
      if (path === '/roads') return Promise.resolve([])
      return Promise.resolve([])
    })

    render(<RoutePlanningPage />)

    expect(await screen.findByText('Bellandur')).toBeInTheDocument()
    expect(screen.getByText(/Rising water/)).toBeInTheDocument()
  })

  it('approves a recommendation', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/recommendations') return Promise.resolve([REC])
      if (path === '/zones') return Promise.resolve([ZONE])
      return Promise.resolve([])
    })
    api.post.mockResolvedValue({})
    const user = userEvent.setup()

    render(<RoutePlanningPage />)
    await user.click(await screen.findByText('APPROVE'))

    expect(api.post).toHaveBeenCalledWith('/recommendations/42/approve')
  })
})
