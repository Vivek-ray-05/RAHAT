import { useState, useEffect, useCallback, useMemo } from 'react'
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
  const [search, setSearch] = useState('')

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

  const zoneName = useCallback((id) => zones.find((z) => z.id === id)?.name || `Zone ${id}`, [zones])

  const groupedByZone = useMemo(() => {
    const query = search.trim().toLowerCase()
    const matches = (s) => {
      if (!query) return true
      return s.name.toLowerCase().includes(query) || zoneName(s.zone_id).toLowerCase().includes(query)
    }

    const groups = new Map()
    for (const s of shelters) {
      if (!matches(s)) continue
      const name = zoneName(s.zone_id)
      if (!groups.has(name)) groups.set(name, [])
      groups.get(name).push(s)
    }
    for (const list of groups.values()) {
      list.sort((a, b) => a.name.localeCompare(b.name))
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [shelters, search, zoneName])

  const visibleCount = groupedByZone.reduce((sum, [, list]) => sum + list.length, 0)

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Shelter Status</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        <div className="border border-gray-800 bg-surface-panel p-6 max-w-3xl">
          <div className="flex justify-between items-center mb-4 gap-4">
            <p className="font-mono text-green-400 text-sm font-bold">
              SHELTERS // {visibleCount}{visibleCount !== shelters.length ? ` of ${shelters.length}` : ''}
            </p>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="SEARCH SHELTER OR ZONE"
              className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-xs px-3 py-1.5 outline-none placeholder:text-gray-600 w-56"
            />
          </div>

          {visibleCount === 0 && (
            <p className="font-mono text-gray-500 text-xs">No shelters match "{search}".</p>
          )}

          <div className="flex flex-col gap-5">
            {groupedByZone.map(([zone, list]) => (
              <div key={zone}>
                <p className="font-mono text-gray-500 text-[10px] tracking-widest uppercase mb-1.5">
                  {zone} // {list.length}
                </p>
                <div className="flex flex-col gap-2">
                  {list.map((s) => (
                    <div key={s.id} className="flex justify-between font-mono text-xs border-b border-gray-800 pb-1.5">
                      <p className="text-gray-300">
                        {s.name}
                        {s.has_medical && <span className="text-gray-600"> // MEDICAL</span>}
                      </p>
                      <span className={`font-bold ${occupancyColor(s.current_occupancy, s.capacity)}`}>
                        {s.current_occupancy}/{s.capacity}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
