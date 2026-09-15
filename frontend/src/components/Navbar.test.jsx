import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import Navbar from './Navbar'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const navigateMock = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => navigateMock }
})

describe('Navbar', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the current role and user id', () => {
    useAuth.mockReturnValue({ user: { id: 7, role: 'zone_admin' }, logout: vi.fn() })

    render(<MemoryRouter><Navbar /></MemoryRouter>)

    expect(screen.getByText(/ZONE_ADMIN.*USER_ID: 7/)).toBeInTheDocument()
  })

  it('logs out and navigates to /login', async () => {
    const logout = vi.fn()
    useAuth.mockReturnValue({ user: { id: 1, role: 'citizen' }, logout })
    const user = userEvent.setup()

    render(<MemoryRouter><Navbar /></MemoryRouter>)
    await user.click(screen.getByText('LOGOUT'))

    expect(logout).toHaveBeenCalled()
    expect(navigateMock).toHaveBeenCalledWith('/login')
  })
})
