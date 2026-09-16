import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import ShelterStatusPage from './ShelterStatusPage'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({ api: { get: vi.fn() } }))

const ZONE_A = { id: 5, name: 'Bellandur' }
const ZONE_B = { id: 6, name: 'Whitefield' }
const NEARLY_FULL_SHELTER = { id: 9, name: 'HSR Hall', zone_id: 5, capacity: 100, current_occupancy: 95, has_medical: true }
const EMPTY_SHELTER = { id: 10, name: 'ITPL Hall', zone_id: 5, capacity: 100, current_occupancy: 10, has_medical: false }
const OTHER_ZONE_SHELTER = { id: 11, name: 'Prestige Grounds', zone_id: 6, capacity: 200, current_occupancy: 20, has_medical: false }

function mockData(shelters, zones = [ZONE_A, ZONE_B]) {
  api.get.mockImplementation((path) => {
    if (path === '/shelters') return Promise.resolve(shelters)
    if (path === '/zones') return Promise.resolve(zones)
    return Promise.resolve([])
  })
}

describe('ShelterStatusPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists shelters grouped under their zone name, with occupancy and medical flag', async () => {
    mockData([NEARLY_FULL_SHELTER])

    render(<ShelterStatusPage />)

    expect(await screen.findByText('HSR Hall')).toBeInTheDocument()
    expect(screen.getByText(/Bellandur/)).toBeInTheDocument()
    expect(screen.getByText(/MEDICAL/)).toBeInTheDocument()
    expect(screen.getByText('95/100')).toBeInTheDocument()
  })

  it('color-codes a nearly-full shelter in red and a mostly-empty one in green', async () => {
    mockData([NEARLY_FULL_SHELTER, EMPTY_SHELTER])

    render(<ShelterStatusPage />)

    const full = await screen.findByText('95/100')
    const empty = await screen.findByText('10/100')
    expect(full.className).toContain('text-red-400')
    expect(empty.className).toContain('text-green-400')
  })

  it('groups shelters from different zones under separate headers', async () => {
    mockData([NEARLY_FULL_SHELTER, OTHER_ZONE_SHELTER])

    render(<ShelterStatusPage />)

    expect(await screen.findByText(/Bellandur.*\/\/ 1/)).toBeInTheDocument()
    expect(screen.getByText(/Whitefield.*\/\/ 1/)).toBeInTheDocument()
  })

  it('filters shelters by search text matching the shelter name', async () => {
    mockData([NEARLY_FULL_SHELTER, OTHER_ZONE_SHELTER])
    const user = userEvent.setup()

    render(<ShelterStatusPage />)
    await screen.findByText('HSR Hall')

    await user.type(screen.getByPlaceholderText(/SEARCH/), 'Prestige')

    expect(screen.queryByText('HSR Hall')).not.toBeInTheDocument()
    expect(screen.getByText('Prestige Grounds')).toBeInTheDocument()
  })

  it('filters shelters by search text matching the zone name', async () => {
    mockData([NEARLY_FULL_SHELTER, OTHER_ZONE_SHELTER])
    const user = userEvent.setup()

    render(<ShelterStatusPage />)
    await screen.findByText('HSR Hall')

    await user.type(screen.getByPlaceholderText(/SEARCH/), 'whitefield')

    expect(screen.queryByText('HSR Hall')).not.toBeInTheDocument()
    expect(screen.getByText('Prestige Grounds')).toBeInTheDocument()
  })

  it('shows a message when no shelter matches the search', async () => {
    mockData([NEARLY_FULL_SHELTER])
    const user = userEvent.setup()

    render(<ShelterStatusPage />)
    await screen.findByText('HSR Hall')

    await user.type(screen.getByPlaceholderText(/SEARCH/), 'nonexistent')

    expect(await screen.findByText(/No shelters match/)).toBeInTheDocument()
  })
})
