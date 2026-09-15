import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'

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
    <span className={`${color} uppercase text-[10px]`} title={info.note}>
      {info.quality}
    </span>
  )
}

export default function ZonalAnalysisPage() {
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setZones(await api.get('/zones'))
    } catch (err) {
      setError(err.message || 'Could not load zones')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Zonal Analysis</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {zones.map((z) => (
            <div key={z.id} className="border border-gray-800 bg-surface-panel p-5">
              <p className="font-mono text-green-400 text-sm font-bold mb-3">{z.name}</p>
              <dl className="font-mono text-xs text-gray-400 flex flex-col gap-1.5">
                <div className="flex justify-between">
                  <dt className="text-gray-600">FLOOD_RISK</dt>
                  <dd className="flex gap-2 items-center">
                    {z.flood_risk_base != null ? z.flood_risk_base.toFixed(1) : 'n/a'}
                    {qualityBadge(z, 'flood_risk_base')}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">POPULATION</dt>
                  <dd className="flex gap-2 items-center">
                    {z.population.toLocaleString()}
                    {qualityBadge(z, 'population')}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">ELDERLY_PCT</dt>
                  <dd>{z.elderly_pct}%</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">ELEVATION_TIER</dt>
                  <dd className="flex gap-2 items-center">
                    {z.elevation_tier}
                    {qualityBadge(z, 'elevation_tier')}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">ELEVATION_M</dt>
                  <dd>{z.elevation_m ?? 'n/a'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">HOSPITALS</dt>
                  <dd className="flex gap-2 items-center">
                    {z.hospital_count}
                    {qualityBadge(z, 'hospital_count')}
                  </dd>
                </div>
              </dl>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
