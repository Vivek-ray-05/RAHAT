import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import CitizenDashboard from './CitizenDashboard'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

vi.mock('../api/client', () => ({ api: { get: vi.fn(), post: vi.fn() } }))
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => vi.fn() }
})

function renderDashboard() {
  return render(
    <MemoryRouter>
      <CitizenDashboard />
    </MemoryRouter>
  )
}

describe('CitizenDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { id: 1 }, logout: vi.fn() })
  })

  it('lists shelters with occupancy and zone name', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([{ id: 5, name: 'Bellandur' }])
      if (path === '/shelters') {
        return Promise.resolve([{ id: 9, name: 'HSR Hall', zone_id: 5, current_occupancy: 40, capacity: 500, has_medical: true }])
      }
      return Promise.resolve([])
    })

    renderDashboard()

    expect(await screen.findByText('HSR Hall')).toBeInTheDocument()
    expect(screen.getByText(/Bellandur.*40\/500.*MEDICAL/)).toBeInTheDocument()
  })

  it('submits an incident report for the selected zone', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([{ id: 5, name: 'Bellandur' }])
      if (path === '/shelters') return Promise.resolve([])
      return Promise.resolve([])
    })
    api.post.mockResolvedValue({})
    const user = userEvent.setup()

    renderDashboard()
    await screen.findByText('SUBMIT_INCIDENT_REPORT')

    await user.selectOptions(screen.getByRole('combobox'), '5')
    await user.type(screen.getByPlaceholderText(/DESCRIBE WHAT/), 'Water rising fast near the main road')
    await user.click(screen.getByText('SUBMIT'))

    expect(api.post).toHaveBeenCalledWith('/citizen-reports', {
      zone_id: 5,
      description: 'Water rising fast near the main road',
    })
    expect(await screen.findByText(/Report submitted/)).toBeInTheDocument()
  })

  it('shows an error and keeps the form when submission fails', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([{ id: 5, name: 'Bellandur' }])
      if (path === '/shelters') return Promise.resolve([])
      return Promise.resolve([])
    })
    api.post.mockRejectedValue(new Error('Zone not found'))
    const user = userEvent.setup()

    renderDashboard()
    await screen.findByText('SUBMIT_INCIDENT_REPORT')

    await user.selectOptions(screen.getByRole('combobox'), '5')
    await user.type(screen.getByPlaceholderText(/DESCRIBE WHAT/), 'Flooding')
    await user.click(screen.getByText('SUBMIT'))

    expect(await screen.findByText(/ERROR: Zone not found/)).toBeInTheDocument()
    expect(screen.queryByText(/Report submitted/)).not.toBeInTheDocument()
  })
})
