import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import DirectionsPage from './DirectionsPage'
import { api } from '../../api/client'
import { useSocket } from '../../context/SocketContext'

vi.mock('../../api/client', () => ({ api: { get: vi.fn() } }))
vi.mock('../../context/SocketContext', () => ({ useSocket: vi.fn() }))

const ZONE = { id: 5, name: 'Bellandur', center_lat: 12.9304, center_lon: 77.6784, flood_risk_base: 9.6 }
const SHELTER = { id: 9, name: 'HSR Hall', lat: 12.9121, lon: 77.6446, capacity: 500, current_occupancy: 50 }

describe('DirectionsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSocket.mockReturnValue({ latestTick: null })
  })

  it('finds and shows the nearest shelter for the selected zone', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([ZONE])
      if (path.startsWith('/shelters/nearest')) {
        return Promise.resolve({ source: 'nearest_available', shelter: SHELTER, distance_km: 3.4 })
      }
      return Promise.resolve([])
    })
    const user = userEvent.setup()

    render(<DirectionsPage />)
    await user.selectOptions(await screen.findByRole('combobox'), '5')
    await user.click(screen.getByText('FIND_NEAREST_SHELTER'))

    expect(api.get).toHaveBeenCalledWith('/shelters/nearest?zone_id=5')
    expect(await screen.findByText('HSR Hall')).toBeInTheDocument()
    expect(screen.getByText(/NEAREST AVAILABLE SHELTER/)).toBeInTheDocument()
    expect(screen.getByText(/3.4 km away/)).toBeInTheDocument()
  })

  it('labels an official evacuation order distinctly', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([ZONE])
      if (path.startsWith('/shelters/nearest')) {
        return Promise.resolve({ source: 'official_recommendation', shelter: SHELTER, distance_km: null })
      }
      return Promise.resolve([])
    })
    const user = userEvent.setup()

    render(<DirectionsPage />)
    await user.selectOptions(await screen.findByRole('combobox'), '5')
    await user.click(screen.getByText('FIND_NEAREST_SHELTER'))

    expect(await screen.findByText(/OFFICIAL EVACUATION ORDER/)).toBeInTheDocument()
  })

  it('surfaces an error when no shelter is available', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([ZONE])
      if (path.startsWith('/shelters/nearest')) return Promise.reject(new Error('No shelter currently has available capacity'))
      return Promise.resolve([])
    })
    const user = userEvent.setup()

    render(<DirectionsPage />)
    await user.selectOptions(await screen.findByRole('combobox'), '5')
    await user.click(screen.getByText('FIND_NEAREST_SHELTER'))

    expect(await screen.findByText(/ERROR: No shelter currently has available capacity/)).toBeInTheDocument()
  })
})
