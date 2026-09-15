import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../context/AuthContext'
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

export default function ZoneStatusPage() {
  const { user } = useAuth()

  const [zone, setZone] = useState(null)
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!user?.zone_id) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    try {
      const [zonesData, reportsData] = await Promise.all([
        api.get('/zones'),
        api.get(`/citizen-reports?zone_id=${user.zone_id}`),
      ])
      setZone(zonesData.find((z) => z.id === user.zone_id) || null)
      setReports(reportsData)
    } catch (err) {
      setError(err.message || 'Could not load zone status')
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => { load() }, [load])

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Zone Status</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && !user?.zone_id && (
        <p className="font-mono text-gray-400 text-sm">No zone assignment on this account yet.</p>
      )}

      {!loading && zone && (
        <>
          <div className="border border-gray-800 bg-surface-panel p-6 mb-6 max-w-xl">
            <p className="font-mono text-green-400 text-sm font-bold mb-4">{zone.name}</p>
            <dl className="font-mono text-xs text-gray-400 flex flex-col gap-1.5">
              <div className="flex justify-between">
                <dt className="text-gray-600">FLOOD_RISK</dt>
                <dd className="flex gap-2 items-center">
                  {zone.flood_risk_base != null ? zone.flood_risk_base.toFixed(1) : 'n/a'}
                  {qualityBadge(zone, 'flood_risk_base')}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">POPULATION</dt>
                <dd className="flex gap-2 items-center">
                  {zone.population.toLocaleString()}
                  {qualityBadge(zone, 'population')}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">ELEVATION_TIER</dt>
                <dd className="flex gap-2 items-center">
                  {zone.elevation_tier}
                  {qualityBadge(zone, 'elevation_tier')}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">HOSPITALS</dt>
                <dd>{zone.hospital_count}</dd>
              </div>
            </dl>
          </div>

          <div className="border border-gray-800 bg-surface-panel p-6 max-w-2xl">
            <p className="font-mono text-amber-400 text-sm font-bold mb-4">
              CITIZEN_REPORTS // {reports.length}
            </p>
            {reports.length === 0 && <p className="font-mono text-gray-500 text-xs">No reports for this zone.</p>}
            <div className="flex flex-col gap-2">
              {reports.map((r) => (
                <div key={r.id} className={`font-mono text-xs border-b border-gray-800 pb-2 ${r.is_sos ? 'text-red-400' : 'text-gray-400'}`}>
                  {r.is_sos && <span className="font-bold mr-2">[SOS]</span>}
                  {r.description}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
