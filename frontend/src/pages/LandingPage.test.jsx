import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import LandingPage from './LandingPage'

const navigateMock = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => navigateMock }
})

function renderLanding() {
  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>
  )
}

describe('LandingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows the boot sequence before the hero section', () => {
    renderLanding()

    expect(screen.queryByText('ENTER_SYSTEM')).not.toBeInTheDocument()
  })

  // The boot sequence runs 8 lines at 400ms apart plus an 800ms pause
  // (~4.4s) before the hero section mounts -- real timers, not fake
  // ones, since the hero's own radar sweep intervals interact badly
  // with vi.advanceTimersByTime.
  it('reveals the hero section with a working ENTER_SYSTEM button once boot completes', async () => {
    renderLanding()

    expect(await screen.findByText('ENTER_SYSTEM', {}, { timeout: 6000 })).toBeInTheDocument()
    expect(screen.getByText('RAHAT')).toBeInTheDocument()

    const user = userEvent.setup()
    await user.click(screen.getByText('ENTER_SYSTEM'))

    expect(navigateMock).toHaveBeenCalledWith('/login')
  }, 8000)
})
