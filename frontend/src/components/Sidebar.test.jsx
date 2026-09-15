import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import Sidebar from './Sidebar'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

function renderSidebar() {
  return render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>
  )
}

describe('Sidebar', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows only the coordinator tabs for a central_coordinator', () => {
    useAuth.mockReturnValue({ user: { role: 'central_coordinator' } })

    renderSidebar()

    expect(screen.getByText('DASHBOARD')).toBeInTheDocument()
    expect(screen.getByText('ROUTE_PLAN')).toBeInTheDocument()
    expect(screen.getByText('SIMULATION')).toBeInTheDocument()
    expect(screen.getByText('ZONAL_ANALYSIS')).toBeInTheDocument()
    expect(screen.getByText('SHELTER_STATUS')).toBeInTheDocument()
    expect(screen.queryByText('SHELTER_MANAGEMENT')).not.toBeInTheDocument()
    expect(screen.queryByText('EMERGENCY_SOS')).not.toBeInTheDocument()
  })

  it('shows only the zone admin tabs for a zone_admin', () => {
    useAuth.mockReturnValue({ user: { role: 'zone_admin' } })

    renderSidebar()

    expect(screen.getByText('ROUTE_PLANNING')).toBeInTheDocument()
    expect(screen.getByText('SHELTER_MANAGEMENT')).toBeInTheDocument()
    expect(screen.getByText('ZONE_STATUS')).toBeInTheDocument()
    expect(screen.queryByText('SIMULATION')).not.toBeInTheDocument()
  })

  it('shows only the citizen tabs for a citizen', () => {
    useAuth.mockReturnValue({ user: { role: 'citizen' } })

    renderSidebar()

    expect(screen.getByText('EMERGENCY_SOS')).toBeInTheDocument()
    expect(screen.getByText('REPORT_FILING')).toBeInTheDocument()
    expect(screen.getByText('DIRECTIONS')).toBeInTheDocument()
    expect(screen.queryByText('ROUTE_PLAN')).not.toBeInTheDocument()
  })

  it('shows only the NDRF tab for ndrf', () => {
    useAuth.mockReturnValue({ user: { role: 'ndrf' } })

    renderSidebar()

    expect(screen.getByText('RESPONSE')).toBeInTheDocument()
    expect(screen.queryByText('DASHBOARD')).not.toBeInTheDocument()
  })
})
