import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import EmergencySOSPage from './EmergencySOSPage'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({ api: { get: vi.fn(), post: vi.fn() } }))

const ZONE = { id: 5, name: 'Bellandur' }

describe('EmergencySOSPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('sends an SOS report flagged is_sos for the selected zone', async () => {
    api.get.mockResolvedValue([ZONE])
    api.post.mockResolvedValue({})
    const user = userEvent.setup()

    render(<EmergencySOSPage />)
    await user.selectOptions(await screen.findByRole('combobox'), '5')
    await user.click(screen.getByText('SEND SOS'))

    expect(api.post).toHaveBeenCalledWith('/citizen-reports', {
      zone_id: 5,
      description: 'SOS -- immediate help needed',
      is_sos: true,
    })
    expect(await screen.findByText('SOS SENT')).toBeInTheDocument()
  })

  it('shows an error when sending fails', async () => {
    api.get.mockResolvedValue([ZONE])
    api.post.mockRejectedValue(new Error('Zone not found'))
    const user = userEvent.setup()

    render(<EmergencySOSPage />)
    await user.selectOptions(await screen.findByRole('combobox'), '5')
    await user.click(screen.getByText('SEND SOS'))

    expect(await screen.findByText(/ERROR: Zone not found/)).toBeInTheDocument()
  })
})
