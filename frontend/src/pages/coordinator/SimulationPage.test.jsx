import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import SimulationPage from './SimulationPage'
import { api } from '../../api/client'
import { useSocket } from '../../context/SocketContext'

vi.mock('../../api/client', () => ({ api: { get: vi.fn(), post: vi.fn() } }))
vi.mock('../../context/SocketContext', () => ({ useSocket: vi.fn() }))

const navigateMock = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => navigateMock }
})

const SCENARIO = { id: 3, name: 'Moderate Monsoon Flood', scenario_type: 'moderate_flood', config_json: { severity: 1.0 } }
const RUNNING_RUN = { id: 7, scenario_id: 3, scenario_name: 'Moderate Monsoon Flood', status: 'running', started_by_name: 'Coordinator One', started_at: '2026-09-15T00:00:00Z', ended_at: null }
const COMPLETED_RUN = { id: 4, scenario_id: 3, scenario_name: 'Moderate Monsoon Flood', status: 'completed', started_by_name: 'Coordinator One', started_at: '2026-09-14T00:00:00Z', ended_at: '2026-09-14T01:00:00Z' }

function renderPage() {
  return render(
    <MemoryRouter>
      <SimulationPage />
    </MemoryRouter>
  )
}

describe('SimulationPage', () => {
  const connect = vi.fn()
  const disconnect = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    useSocket.mockReturnValue({ connect, disconnect, connected: false, latestTick: null, error: '' })
  })

  it('lists scenarios in the start picker and runs in the run list', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/scenarios') return Promise.resolve([SCENARIO])
      if (path === '/simulation') return Promise.resolve([RUNNING_RUN])
      return Promise.resolve([])
    })

    renderPage()

    expect(await screen.findByText('Moderate Monsoon Flood')).toBeInTheDocument()
    expect(screen.getByText(/RUN_7/)).toBeInTheDocument()
    expect(screen.getByText('running')).toBeInTheDocument()
  })

  it('starts a new run for the selected scenario and watches it', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/scenarios') return Promise.resolve([SCENARIO])
      if (path === '/simulation') return Promise.resolve([])
      return Promise.resolve([])
    })
    api.post.mockResolvedValue({ id: 9, scenario_id: 3, status: 'running' })
    const user = userEvent.setup()

    renderPage()
    await screen.findByText('START_NEW_RUN')

    await user.selectOptions(screen.getByRole('combobox'), '3')
    await user.click(screen.getByText('START'))

    expect(api.post).toHaveBeenCalledWith('/simulation/start', { scenario_id: 3 })
    expect(connect).toHaveBeenCalledWith(9)
  })

  it('advances a tick for a running run', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/scenarios') return Promise.resolve([])
      if (path === '/simulation') return Promise.resolve([RUNNING_RUN])
      return Promise.resolve([])
    })
    api.post.mockResolvedValue({})
    const user = userEvent.setup()

    renderPage()
    await user.click(await screen.findByText('TICK'))

    expect(api.post).toHaveBeenCalledWith('/simulation/7/tick')
  })

  it('pauses a running run', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/scenarios') return Promise.resolve([])
      if (path === '/simulation') return Promise.resolve([RUNNING_RUN])
      return Promise.resolve([])
    })
    api.post.mockResolvedValue({})
    const user = userEvent.setup()

    renderPage()
    await user.click(await screen.findByText('PAUSE'))

    expect(api.post).toHaveBeenCalledWith('/simulation/7/pause')
  })

  it('navigates to the report page for a completed run', async () => {
    api.get.mockImplementation((path) => {
      if (path === '/scenarios') return Promise.resolve([])
      if (path === '/simulation') return Promise.resolve([COMPLETED_RUN])
      return Promise.resolve([])
    })
    const user = userEvent.setup()

    renderPage()
    await user.click(await screen.findByText('VIEW_REPORT'))

    expect(navigateMock).toHaveBeenCalledWith('/report/4')
  })

  it('shows the latest tick once one arrives', async () => {
    api.get.mockResolvedValue([])
    useSocket.mockReturnValue({
      connect, disconnect, connected: true,
      latestTick: { tick_number: 2, timestamp: '2026-09-15T00:01:00Z' }, error: '',
    })

    renderPage()

    expect(await screen.findByText(/tick 2/)).toBeInTheDocument()
  })
})
