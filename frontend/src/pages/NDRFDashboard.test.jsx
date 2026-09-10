import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import NDRFDashboard from './NDRFDashboard'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

vi.mock('../api/client', () => ({ api: { get: vi.fn() } }))
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const navigateMock = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => navigateMock }
})

function renderDashboard() {
  return render(
    <MemoryRouter>
      <NDRFDashboard />
    </MemoryRouter>
  )
}

describe('NDRFDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows a message when the account has no zone assignment', async () => {
    useAuth.mockReturnValue({ user: { id: 1, zone_id: null }, logout: vi.fn() })

    renderDashboard()

    expect(await screen.findByText(/no zone assignment/i)).toBeInTheDocument()
    expect(api.get).not.toHaveBeenCalled()
  })

  it('shows a no-route message when the assigned zone has no computed route yet', async () => {
    useAuth.mockReturnValue({ user: { id: 2, zone_id: 5 }, logout: vi.fn() })
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([{ id: 5, name: 'Bellandur' }])
      const err = new Error('not found')
      err.status = 404
      return Promise.reject(err)
    })

    renderDashboard()

    expect(await screen.findByText(/ASSIGNED_ZONE.*Bellandur/)).toBeInTheDocument()
    expect(screen.getByText(/no evacuation route computed/i)).toBeInTheDocument()
  })

  it('renders the route status, target shelter, and ETA when a route exists', async () => {
    useAuth.mockReturnValue({ user: { id: 3, zone_id: 5 }, logout: vi.fn() })
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([{ id: 5, name: 'Bellandur' }])
      if (path === '/zones/5/routes') {
        return Promise.resolve({ status: 'active', to_shelter_id: 9, eta: 14 })
      }
      if (path === '/shelters') return Promise.resolve([{ id: 9, name: 'HSR Community Hall' }])
      throw new Error(`unexpected path ${path}`)
    })

    renderDashboard()

    expect(await screen.findByText(/active/i)).toBeInTheDocument()
    expect(screen.getByText(/HSR Community Hall/)).toBeInTheDocument()
    expect(screen.getByText(/14 min/)).toBeInTheDocument()
  })

  it('logs out and navigates to /login', async () => {
    const logout = vi.fn()
    useAuth.mockReturnValue({ user: { id: 1, zone_id: null }, logout })
    const user = userEvent.setup()

    renderDashboard()
    await user.click(await screen.findByText('LOGOUT'))

    expect(logout).toHaveBeenCalled()
    expect(navigateMock).toHaveBeenCalledWith('/login')
  })

  it('surfaces a non-404 load error instead of silently failing', async () => {
    useAuth.mockReturnValue({ user: { id: 4, zone_id: 5 }, logout: vi.fn() })
    api.get.mockImplementation((path) => {
      if (path === '/zones') return Promise.resolve([{ id: 5, name: 'Bellandur' }])
      return Promise.reject(new Error('server exploded'))
    })

    renderDashboard()

    expect(await screen.findByText(/ERROR: server exploded/)).toBeInTheDocument()
  })
})
