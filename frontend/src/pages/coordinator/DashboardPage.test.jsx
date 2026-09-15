import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import DashboardPage from './DashboardPage'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({ api: { get: vi.fn() } }))

const HIGH_RISK_ZONE = {
  id: 1, name: 'Bellandur', population: 11736, elevation_tier: 'low', flood_risk_base: 9.6,
  data_quality_json: { flood_risk_base: { quality: 'real', note: 'SRTM elevation' } },
}
const LOW_RISK_ZONE = {
  id: 2, name: 'Electronic City', population: 13552, elevation_tier: 'high', flood_risk_base: 0.9,
  data_quality_json: {},
}

describe('DashboardPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders zones sorted by risk, highest first', async () => {
    api.get.mockResolvedValue([LOW_RISK_ZONE, HIGH_RISK_ZONE])

    render(<DashboardPage />)

    const names = (await screen.findAllByText(/Bellandur|Electronic City/)).map((el) => el.textContent)
    expect(names[0]).toBe('Bellandur')
  })

  it('color-codes a high-risk zone in red', async () => {
    api.get.mockResolvedValue([HIGH_RISK_ZONE])

    render(<DashboardPage />)

    const riskText = await screen.findByText(/risk 9\.6/)
    expect(riskText.className).toContain('text-red-400')
  })

  it('color-codes a low-risk zone in green', async () => {
    api.get.mockResolvedValue([LOW_RISK_ZONE])

    render(<DashboardPage />)

    const riskText = await screen.findByText(/risk 0\.9/)
    expect(riskText.className).toContain('text-green-400')
  })

  it('counts zones at or above the elevated-risk threshold', async () => {
    api.get.mockResolvedValue([LOW_RISK_ZONE, HIGH_RISK_ZONE])

    render(<DashboardPage />)

    expect(await screen.findByText(/1 zone\(s\) with elevated baseline flood risk/)).toBeInTheDocument()
  })
})
