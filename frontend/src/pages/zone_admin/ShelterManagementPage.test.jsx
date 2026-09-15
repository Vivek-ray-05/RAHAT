import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import ShelterManagementPage from './ShelterManagementPage'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'

vi.mock('../../api/client', () => ({ api: { get: vi.fn(), patch: vi.fn() } }))
vi.mock('../../context/AuthContext', () => ({ useAuth: vi.fn() }))

const SHELTER = { id: 9, name: 'HSR Hall', zone_id: 5, capacity: 500, current_occupancy: 100, has_medical: false }

describe('ShelterManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { id: 1, zone_id: 5 } })
  })

  it('renders the zone admin their own zone shelters', async () => {
    api.get.mockResolvedValue([SHELTER])

    render(<ShelterManagementPage />)

    expect(await screen.findByText('HSR Hall')).toBeInTheDocument()
    expect(screen.getByText('100/500')).toBeInTheDocument()
  })

  it('edits and saves a new occupancy count', async () => {
    api.get.mockResolvedValue([SHELTER])
    api.patch.mockResolvedValue({})
    const user = userEvent.setup()

    render(<ShelterManagementPage />)
    await user.click(await screen.findByText('EDIT'))

    const input = screen.getByRole('spinbutton')
    await user.clear(input)
    await user.type(input, '250')
    await user.click(screen.getByText('SAVE'))

    expect(api.patch).toHaveBeenCalledWith('/shelters/9', { current_occupancy: 250 })
  })

  it('shows an error when the update fails', async () => {
    api.get.mockResolvedValue([SHELTER])
    api.patch.mockRejectedValue(new Error('current_occupancy must be between 0 and this shelter\'s capacity (500)'))
    const user = userEvent.setup()

    render(<ShelterManagementPage />)
    await user.click(await screen.findByText('EDIT'))
    await user.click(screen.getByText('SAVE'))

    expect(await screen.findByText(/ERROR: current_occupancy must be between/)).toBeInTheDocument()
  })
})
