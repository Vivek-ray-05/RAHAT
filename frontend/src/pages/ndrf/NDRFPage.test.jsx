import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import NDRFPage from './NDRFPage'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { useSocket } from '../../context/SocketContext'

vi.mock('../../api/client', () => ({ api: { get: vi.fn(), post: vi.fn() } }))
vi.mock('../../context/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../../context/SocketContext', () => ({ useSocket: vi.fn() }))

const ZONE = { id: 5, name: 'Bellandur', center_lat: 12.9304, center_lon: 77.6784, flood_risk_base: 9.6 }

describe('NDRFPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSocket.mockReturnValue({ latestTick: null })
  })

  it('shows a message when the account has no zone assignment', async () => {
    useAuth.mockReturnValue({ user: { id: 1, zone_id: null } })

    render(<NDRFPage />)

    expect(await screen.findByText(/no zone assignment/i)).toBeInTheDocument()
  })

  it('renders the assigned zone, route status, and citizen reports', async () => {
    useAuth.mockReturnValue({ user: { id: 2, zone_id: 5 } })
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([ZONE])
      if (path === '/shelters') return Promise.resolve([])
      if (path === '/roads') return Promise.resolve([])
      if (path.startsWith('/citizen-reports')) return Promise.resolve([{ id: 1, description: 'Water rising', is_sos: true }])
      if (path === '/zones/5/routes') return Promise.resolve({ status: 'usable', eta: 12 })
      throw new Error(`unexpected path ${path}`)
    })

    render(<NDRFPage />)

    expect(await screen.findByText(/ASSIGNED_ZONE.*Bellandur/)).toBeInTheDocument()
    expect(screen.getByText(/usable/)).toBeInTheDocument()
    expect(screen.getByText(/Water rising/)).toBeInTheDocument()
    expect(screen.getByText('[SOS]')).toBeInTheDocument()
  })
})
