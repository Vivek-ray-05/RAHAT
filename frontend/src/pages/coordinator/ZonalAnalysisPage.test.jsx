import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import ZonalAnalysisPage from './ZonalAnalysisPage'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({ api: { get: vi.fn() } }))

const ZONE = {
  id: 1, name: 'Bellandur', population: 11736, elderly_pct: 8.2,
  elevation_tier: 'low', elevation_m: 870, hospital_count: 3, flood_risk_base: 9.6,
  data_quality_json: {
    flood_risk_base: { quality: 'real', note: 'SRTM elevation data' },
    population: { quality: 'estimated', note: 'building-derived' },
  },
}

describe('ZonalAnalysisPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders the full per-zone breakdown', async () => {
    api.get.mockResolvedValue([ZONE])

    render(<ZonalAnalysisPage />)

    expect(await screen.findByText('Bellandur')).toBeInTheDocument()
    expect(screen.getByText('9.6')).toBeInTheDocument()
    expect(screen.getByText('11,736')).toBeInTheDocument()
    expect(screen.getByText('8.2%')).toBeInTheDocument()
    expect(screen.getByText('low')).toBeInTheDocument()
    expect(screen.getByText('870')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('surfaces a load error', async () => {
    api.get.mockRejectedValue(new Error('zones unavailable'))

    render(<ZonalAnalysisPage />)

    expect(await screen.findByText(/ERROR: zones unavailable/)).toBeInTheDocument()
  })
})
