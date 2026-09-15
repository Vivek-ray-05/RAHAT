import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'

function occupancyColor(current, capacity) {
  const pct = capacity > 0 ? current / capacity : 0
  if (pct >= 0.9) return 'text-red-400'
  if (pct >= 0.6) return 'text-amber-400'
  return 'text-green-400'
}

export default function ShelterStatusPage() {
  const [shelters, setShelters] = useState([])
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [sheltersData, zonesData] = await Promise.all([api.get('/shelters'), api.get('/zones')])
      setShelters(sheltersData)
      setZones(zonesData)
    } catch (err) {
      setError(err.message || 'Could not load shelters')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const zoneName = (id) => zones.find((z) => z.id === id)?.name || `Zone ${id}`

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Shelter Status</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        <div className="border border-gray-800 bg-surface-panel p-6 max-w-3xl">
          <p className="font-mono text-green-400 text-sm font-bold mb-4">SHELTERS // {shelters.length}</p>
          <div className="flex flex-col gap-2">
            {shelters.map((s) => (
              <div key={s.id} className="flex justify-between font-mono text-xs border-b border-gray-800 pb-1.5">
                <div>
                  <p className="text-gray-300">{s.name}</p>
                  <p className="text-gray-600">{zoneName(s.zone_id)}{s.has_medical ? ' // MEDICAL' : ''}</p>
                </div>
                <span className={`font-bold ${occupancyColor(s.current_occupancy, s.capacity)}`}>
                  {s.current_occupancy}/{s.capacity}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
