import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import RoutePlanPage from './RoutePlanPage'
import { api } from '../../api/client'
import { useSocket } from '../../context/SocketContext'

vi.mock('../../api/client', () => ({ api: { get: vi.fn(), post: vi.fn() } }))
vi.mock('../../context/SocketContext', () => ({ useSocket: vi.fn() }))

const ZONE = { id: 1, name: 'Bellandur', center_lat: 12.9304, center_lon: 77.6784, flood_risk_base: 9.6 }
const SHELTER = { id: 9, name: 'HSR Hall', lat: 12.9121, lon: 77.6446, capacity: 500, current_occupancy: 0 }
const ROAD = { id: 3, from_zone_id: 1, to_zone_id: 2, is_blocked: false, distance_km: 4.2 }
const RUN = { id: 7, scenario_id: 3, scenario_name: 'Moderate Monsoon Flood', status: 'running', started_by_name: 'X', started_at: '2026-09-15T00:00:00Z', ended_at: null }

describe('RoutePlanPage', () => {
  const connect = vi.fn()
  const disconnect = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    useSocket.mockReturnValue({ connect, disconnect, latestTick: null })
  })

  it('loads zones, shelters, roads, and runs, and connects to the running run', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([ZONE])
      if (path === '/shelters') return Promise.resolve([SHELTER])
      if (path === '/roads') return Promise.resolve([ROAD])
      if (path === '/simulation') return Promise.resolve([RUN])
      return Promise.resolve([])
    })

    render(<RoutePlanPage />)

    await screen.findByText('Route Plan')
    expect(connect).toHaveBeenCalledWith(7)
  })

  it('surfaces a load error', async () => {
    api.get.mockRejectedValue(new Error('server exploded'))

    render(<RoutePlanPage />)

    expect(await screen.findByText(/ERROR: server exploded/)).toBeInTheDocument()
  })
})
