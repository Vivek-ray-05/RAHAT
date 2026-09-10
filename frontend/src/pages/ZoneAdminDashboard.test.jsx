import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import ZoneAdminDashboard from './ZoneAdminDashboard'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

vi.mock('../api/client', () => ({ api: { get: vi.fn(), post: vi.fn() } }))
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const navigateMock = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => navigateMock }
})

const REC = {
  id: 42,
  status: 'pending_review',
  payload_json: {
    zone_id: 5,
    zone_name: 'Bellandur',
    priority_score: 0.9,
    risk_score: 8.1,
    reason: 'Rising water level',
    assigned_shelter_id: null,
    assigned_population: 0,
  },
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <ZoneAdminDashboard />
    </MemoryRouter>
  )
}

describe('ZoneAdminDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { id: 1 }, logout: vi.fn() })
  })

  it('shows an empty state when there are no pending recommendations', async () => {
    api.get.mockImplementation((path) => (path === '/recommendations' ? Promise.resolve([]) : Promise.resolve([])))

    renderDashboard()

    expect(await screen.findByText(/no pending recommendations/i)).toBeInTheDocument()
  })

  it('renders a pending recommendation with its zone, reason, and scores', async () => {
    api.get.mockImplementation((path) => (path === '/recommendations' ? Promise.resolve([REC]) : Promise.resolve([])))

    renderDashboard()

    expect(await screen.findByText('Bellandur')).toBeInTheDocument()
    expect(screen.getByText(/Rising water level/)).toBeInTheDocument()
    expect(screen.getByText('PENDING_REVIEW')).toBeInTheDocument()
  })

  it('approves a recommendation and reloads the queue', async () => {
    api.get.mockImplementation((path) => (path === '/recommendations' ? Promise.resolve([REC]) : Promise.resolve([])))
    api.post.mockResolvedValue({})
    const user = userEvent.setup()

    renderDashboard()
    await user.click(await screen.findByText('APPROVE'))

    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/recommendations/42/approve'))
    expect(api.get).toHaveBeenCalledTimes(4) // initial load (2 calls) + reload after approve (2 calls)
  })

  it('rejects a recommendation with a reason', async () => {
    api.get.mockImplementation((path) => (path === '/recommendations' ? Promise.resolve([REC]) : Promise.resolve([])))
    api.post.mockResolvedValue({})
    const user = userEvent.setup()

    renderDashboard()
    await user.click(await screen.findByText('REJECT'))

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith('/recommendations/42/reject', { reason: 'Rejected by zone admin' })
    )
  })

  it('modifies a recommendation with an edited shelter and population before submitting', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/recommendations') return Promise.resolve([REC])
      if (path === '/shelters') return Promise.resolve([{ id: 9, name: 'HSR Hall', current_occupancy: 0, capacity: 500 }])
      return Promise.resolve([])
    })
    api.post.mockResolvedValue({})
    const user = userEvent.setup()

    renderDashboard()
    await user.click(await screen.findByText('MODIFY'))

    const shelterSelect = screen.getByRole('combobox')
    await user.selectOptions(shelterSelect, '9')
    const populationInput = screen.getByPlaceholderText('ASSIGNED POPULATION')
    await user.clear(populationInput)
    await user.type(populationInput, '250')
    await user.click(screen.getByText('SAVE_AND_APPROVE'))

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith('/recommendations/42/modify', {
        modified_payload: expect.objectContaining({ assigned_shelter_id: 9, assigned_population: 250 }),
        reason: undefined,
      })
    )
  })

  it('surfaces an error when approve fails', async () => {
    api.get.mockImplementation((path) => (path === '/recommendations' ? Promise.resolve([REC]) : Promise.resolve([])))
    api.post.mockRejectedValue(new Error('zone mismatch'))
    const user = userEvent.setup()

    renderDashboard()
    await user.click(await screen.findByText('APPROVE'))

    expect(await screen.findByText(/ERROR: zone mismatch/)).toBeInTheDocument()
  })
})
