import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import ShelterStatusPage from './ShelterStatusPage'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({ api: { get: vi.fn() } }))

const ZONE = { id: 5, name: 'Bellandur' }
const NEARLY_FULL_SHELTER = { id: 9, name: 'HSR Hall', zone_id: 5, capacity: 100, current_occupancy: 95, has_medical: true }
const EMPTY_SHELTER = { id: 10, name: 'ITPL Hall', zone_id: 5, capacity: 100, current_occupancy: 10, has_medical: false }

describe('ShelterStatusPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists shelters with zone name and occupancy', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/shelters') return Promise.resolve([NEARLY_FULL_SHELTER])
      if (path === '/zones') return Promise.resolve([ZONE])
      return Promise.resolve([])
    })

    render(<ShelterStatusPage />)

    expect(await screen.findByText('HSR Hall')).toBeInTheDocument()
    expect(screen.getByText(/Bellandur.*MEDICAL/)).toBeInTheDocument()
    expect(screen.getByText('95/100')).toBeInTheDocument()
  })

  it('color-codes a nearly-full shelter in red and a mostly-empty one in green', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/shelters') return Promise.resolve([NEARLY_FULL_SHELTER, EMPTY_SHELTER])
      if (path === '/zones') return Promise.resolve([ZONE])
      return Promise.resolve([])
    })

    render(<ShelterStatusPage />)

    const full = await screen.findByText('95/100')
    const empty = await screen.findByText('10/100')
    expect(full.className).toContain('text-red-400')
    expect(empty.className).toContain('text-green-400')
  })
})
