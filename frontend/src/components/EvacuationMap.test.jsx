import { render, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import EvacuationMap from './EvacuationMap'
import { api } from '../api/client'
import { useSocket } from '../context/SocketContext'

vi.mock('../api/client', () => ({ api: { get: vi.fn() } }))
vi.mock('../context/SocketContext', () => ({ useSocket: vi.fn() }))

const ZONE = { id: 1, name: 'Bellandur', center_lat: 12.9304, center_lon: 77.6784, flood_risk_base: 9.6 }
const SHELTER = { id: 9, name: 'HSR Hall', lat: 12.9121, lon: 77.6446, capacity: 500, current_occupancy: 100 }

describe('EvacuationMap', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSocket.mockReturnValue({ latestTick: null })
  })

  it('renders without crashing given real zone/shelter data', () => {
    expect(() => render(<EvacuationMap zones={[ZONE]} shelters={[SHELTER]} />)).not.toThrow()
  })

  it('renders without crashing given no data at all', () => {
    expect(() => render(<EvacuationMap />)).not.toThrow()
  })

  it('fetches routes for the given simulation run on mount', async () => {
    api.get.mockResolvedValue([])

    render(<EvacuationMap zones={[ZONE]} shelters={[SHELTER]} simulationRunId={7} />)

    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/routes?simulation_run_id=7'))
  })

  it('does not fetch anything when no simulationRunId is given', () => {
    render(<EvacuationMap zones={[ZONE]} shelters={[SHELTER]} />)

    expect(api.get).not.toHaveBeenCalled()
  })

  it('also refetches roads when a roads prop was provided', async () => {
    api.get.mockResolvedValue([])

    render(<EvacuationMap zones={[ZONE]} shelters={[SHELTER]} roads={[]} simulationRunId={7} />)

    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/roads'))
  })

  it('refetches routes when a new tick arrives', async () => {
    api.get.mockResolvedValue([])
    useSocket.mockReturnValue({ latestTick: { id: 1, tick_number: 0 } })

    const { rerender } = render(<EvacuationMap zones={[ZONE]} shelters={[SHELTER]} simulationRunId={7} />)
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1))

    useSocket.mockReturnValue({ latestTick: { id: 2, tick_number: 1 } })
    rerender(<EvacuationMap zones={[ZONE]} shelters={[SHELTER]} simulationRunId={7} />)

    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2))
  })
})
