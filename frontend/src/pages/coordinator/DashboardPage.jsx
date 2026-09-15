import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'

// Same risk scale as the map's zone markers (EvacuationMap.jsx) --
// this page and the map should read as one consistent color language.
function riskColor(risk) {
  if (risk == null) return 'text-gray-500'
  if (risk >= 7) return 'text-red-400'
  if (risk >= 5) return 'text-amber-400'
  if (risk >= 3) return 'text-yellow-400'
  return 'text-green-400'
}

const QUALITY_COLOR = {
  real: 'text-green-400',
  derived: 'text-amber-400',
  estimated: 'text-gray-400',
  unavailable: 'text-gray-600',
}

function qualityBadge(zone, field) {
  const info = zone.data_quality_json?.[field]
  if (!info) return null
  const color = QUALITY_COLOR[info.quality] || 'text-gray-500'
  return (
    <span className={`${color} uppercase`} title={info.note}>
      {info.quality}
    </span>
  )
}

export default function DashboardPage() {
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setZones(await api.get('/zones'))
    } catch (err) {
      setError(err.message || 'Could not load city data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const highRiskZones = zones.filter((z) => (z.flood_risk_base ?? 0) >= 5)
  const sorted = [...zones].sort((a, b) => (b.flood_risk_base ?? 0) - (a.flood_risk_base ?? 0))

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Dashboard</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        <div className="border border-gray-800 bg-surface-panel p-6 max-w-3xl">
          <p className="font-mono text-green-400 text-sm font-bold mb-4">
            CITY_OVERVIEW // {zones.length} ZONES
          </p>
          <p className="font-mono text-gray-500 text-xs mb-3">
            {highRiskZones.length} zone(s) with elevated baseline flood risk
            <span className="text-gray-700"> // hover a badge for data source</span>
          </p>
          <div className="flex flex-col gap-2 max-h-[60vh] overflow-y-auto">
            {sorted.map((z) => (
              <div key={z.id} className="flex justify-between font-mono text-xs border-b border-gray-800 pb-1">
                <span className="text-gray-300">{z.name}</span>
                <span className="text-gray-600 flex gap-2 items-center">
                  <span title={z.data_quality_json?.population?.note}>
                    pop {z.population.toLocaleString()}
                  </span>
                  //
                  <span title={z.data_quality_json?.elevation_tier?.note}>{z.elevation_tier}</span>
                  //
                  <span className={`font-bold ${riskColor(z.flood_risk_base)}`}>
                    risk {z.flood_risk_base != null ? z.flood_risk_base.toFixed(1) : 'n/a'}
                  </span>
                  {qualityBadge(z, 'flood_risk_base')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
