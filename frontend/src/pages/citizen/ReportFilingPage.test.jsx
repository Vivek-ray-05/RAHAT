import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import ReportFilingPage from './ReportFilingPage'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({ api: { get: vi.fn(), post: vi.fn() } }))

const ZONE = { id: 5, name: 'Bellandur' }

describe('ReportFilingPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('submits a non-SOS report for the selected zone', async () => {
    api.get.mockResolvedValue([ZONE])
    api.post.mockResolvedValue({})
    const user = userEvent.setup()

    render(<ReportFilingPage />)
    await user.selectOptions(await screen.findByRole('combobox'), '5')
    await user.type(screen.getByPlaceholderText(/DESCRIBE WHAT/), 'Minor puddling near the main road')
    await user.click(screen.getByText('SUBMIT'))

    expect(api.post).toHaveBeenCalledWith('/citizen-reports', {
      zone_id: 5,
      description: 'Minor puddling near the main road',
    })
    expect(await screen.findByText(/Report submitted/)).toBeInTheDocument()
  })

  it('shows an error when submission fails', async () => {
    api.get.mockResolvedValue([ZONE])
    api.post.mockRejectedValue(new Error('Zone not found'))
    const user = userEvent.setup()

    render(<ReportFilingPage />)
    await user.selectOptions(await screen.findByRole('combobox'), '5')
    await user.type(screen.getByPlaceholderText(/DESCRIBE WHAT/), 'Flooding')
    await user.click(screen.getByText('SUBMIT'))

    expect(await screen.findByText(/ERROR: Zone not found/)).toBeInTheDocument()
  })
})
