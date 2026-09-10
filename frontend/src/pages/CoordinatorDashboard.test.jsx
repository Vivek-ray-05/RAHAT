import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import CoordinatorDashboard from './CoordinatorDashboard'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useSocket } from '../context/SocketContext'

vi.mock('../api/client', () => ({ api: { get: vi.fn() } }))
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../context/SocketContext', () => ({ useSocket: vi.fn() }))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => vi.fn() }
})

const ZONE = {
  id: 5,
  name: 'Bellandur',
  population: 92000,
  elevation_tier: 'low',
  flood_risk_base: 9.6,
  data_quality_json: {
    flood_risk_base: { quality: 'real', note: 'Derived from SRTM elevation data.' },
    population: { quality: 'real', note: '2011 census, projected.' },
    elevation_tier: { quality: 'real', note: 'SRTM 30m DEM.' },
  },
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <CoordinatorDashboard />
    </MemoryRouter>
  )
}

describe('CoordinatorDashboard', () => {
  let connect, disconnect

  beforeEach(() => {
    vi.clearAllMocks()
    connect = vi.fn()
    disconnect = vi.fn()
    useAuth.mockReturnValue({ user: { id: 1 }, logout: vi.fn() })
    useSocket.mockReturnValue({ connect, disconnect, connected: false, latestTick: null, error: '' })
  })

  it('renders each zone with its baseline flood risk and a quality badge', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([ZONE])
      if (path === '/recommendations') return Promise.resolve([])
      return Promise.resolve([])
    })

    renderDashboard()

    expect(await screen.findByText('Bellandur')).toBeInTheDocument()
    expect(screen.getByText(/risk 9\.6/)).toBeInTheDocument()
    expect(screen.getByText('real')).toBeInTheDocument()
  })

  it('counts zones at or above the elevated-risk threshold', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([ZONE, { ...ZONE, id: 6, name: 'Low Risk Zone', flood_risk_base: 1.0 }])
      if (path === '/recommendations') return Promise.resolve([])
      return Promise.resolve([])
    })

    renderDashboard()

    expect(await screen.findByText(/1 zone\(s\) with elevated baseline flood risk/)).toBeInTheDocument()
  })

  it('shows pending recommendations with their zone and reason', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([])
      if (path === '/recommendations') {
        return Promise.resolve([{ id: 1, payload_json: { zone_name: 'Bellandur', reason: 'Rising water level' } }])
      }
      return Promise.resolve([])
    })

    renderDashboard()

    expect(await screen.findByText('PENDING_APPROVALS // 1')).toBeInTheDocument()
    expect(screen.getByText('Rising water level')).toBeInTheDocument()
  })

  it('connects to the tick stream for the entered simulation run id', async () => {
    api.get.mockResolvedValue([])
    const user = userEvent.setup()

    renderDashboard()
    await screen.findByText('LIVE_TICK_STREAM // DISCONNECTED')

    await user.type(screen.getByPlaceholderText('SIMULATION RUN ID'), '7')
    await user.click(screen.getByText('WATCH'))

    expect(connect).toHaveBeenCalledWith(7)
  })

  it('shows the latest tick once one arrives', async () => {
    api.get.mockResolvedValue([])
    useSocket.mockReturnValue({
      connect, disconnect, connected: true,
      latestTick: { tick_number: 4, timestamp: '2026-09-10T00:00:00Z' }, error: '',
    })

    renderDashboard()

    expect(await screen.findByText(/tick 4/)).toBeInTheDocument()
  })
})
