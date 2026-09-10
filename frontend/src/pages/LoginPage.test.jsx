import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import LoginPage from './LoginPage'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const navigateMock = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => navigateMock }
})

function renderLogin() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  )
}

describe('LoginPage', () => {
  let loginWithPassword, requestOtp, verifyOtp

  beforeEach(() => {
    vi.clearAllMocks()
    loginWithPassword = vi.fn()
    requestOtp = vi.fn()
    verifyOtp = vi.fn()
    useAuth.mockReturnValue({ loginWithPassword, requestOtp, verifyOtp })
  })

  it('defaults to the zone admin password form', () => {
    renderLogin()

    expect(screen.getByPlaceholderText('EMAIL')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('PASSWORD')).toBeInTheDocument()
  })

  it('switches to the OTP form for NDRF/citizen roles', async () => {
    const user = userEvent.setup()
    renderLogin()

    await user.click(screen.getByText('CITIZEN'))

    expect(screen.getByPlaceholderText('PHONE')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText('EMAIL')).not.toBeInTheDocument()
  })

  it('logs in with password and navigates to the role home on success', async () => {
    loginWithPassword.mockResolvedValue({ role: 'zone_admin' })
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText('EMAIL'), 'za@rahat.dev')
    await user.type(screen.getByPlaceholderText('PASSWORD'), 'demo1234')
    await user.click(screen.getByText('AUTHENTICATE →'))

    expect(loginWithPassword).toHaveBeenCalledWith('za@rahat.dev', 'demo1234', 'zone_admin')
    expect(navigateMock).toHaveBeenCalledWith('/dashboard/zone')
  })

  it('shows an error message when password login fails', async () => {
    loginWithPassword.mockRejectedValue(new Error('Invalid credentials'))
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText('EMAIL'), 'za@rahat.dev')
    await user.type(screen.getByPlaceholderText('PASSWORD'), 'wrong')
    await user.click(screen.getByText('AUTHENTICATE →'))

    expect(await screen.findByText(/ERROR: Invalid credentials/)).toBeInTheDocument()
    expect(navigateMock).not.toHaveBeenCalled()
  })

  it('requests then verifies an OTP for the citizen role', async () => {
    requestOtp.mockResolvedValue({ dev_otp: '1234' })
    verifyOtp.mockResolvedValue({ role: 'citizen' })
    const user = userEvent.setup()
    renderLogin()

    await user.click(screen.getByText('CITIZEN'))
    await user.type(screen.getByPlaceholderText('PHONE'), '9110001111')
    await user.click(screen.getByText('SEND_CODE →'))

    expect(requestOtp).toHaveBeenCalledWith('9110001111')
    expect(await screen.findByPlaceholderText('CODE')).toBeInTheDocument()
    expect(screen.getByText((_, el) => el?.textContent === 'DEV_MODE // CODE: 1234')).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText('CODE'), '1234')
    await user.click(screen.getByText('VERIFY →'))

    expect(verifyOtp).toHaveBeenCalledWith('9110001111', '1234')
    expect(navigateMock).toHaveBeenCalledWith('/dashboard/citizen')
  })
})
