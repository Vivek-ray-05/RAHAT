import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'
import EvacuationMap from '../../components/EvacuationMap'

const SOURCE_LABEL = {
  official_recommendation: 'OFFICIAL EVACUATION ORDER',
  nearest_available: 'NEAREST AVAILABLE SHELTER (straight-line distance)',
}

export default function DirectionsPage() {
  const [zones, setZones] = useState([])
  const [selectedZoneId, setSelectedZoneId] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [finding, setFinding] = useState(false)
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

  async function handleFind(e) {
    e.preventDefault()
    setFinding(true)
    setError('')
    setResult(null)
    try {
      const data = await api.get(`/shelters/nearest?zone_id=${selectedZoneId}`)
      setResult(data)
    } catch (err) {
      setError(err.message || 'Could not find a shelter for this zone')
    } finally {
      setFinding(false)
    }
  }

  const myZone = zones.find((z) => z.id === Number(selectedZoneId))

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Directions</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        <>
          <form onSubmit={handleFind} className="flex gap-3 mb-6">
            <select
              value={selectedZoneId}
              onChange={(e) => setSelectedZoneId(e.target.value)}
              required
              className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-xs px-3 py-2 outline-none"
            >
              <option value="" className="bg-black">SELECT YOUR ZONE</option>
              {zones.map((z) => (
                <option key={z.id} value={z.id} className="bg-black">{z.name}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={!selectedZoneId || finding}
              className="font-mono text-green-400 text-xs tracking-widest border border-green-500 px-4 py-2 hover:bg-green-500/10 disabled:opacity-40"
            >
              {finding ? 'FINDING...' : 'FIND_NEAREST_SHELTER'}
            </button>
          </form>

          {result && myZone && (
            <>
              <div className="border border-gray-800 bg-surface-panel p-6 mb-6 max-w-2xl">
                <p className="font-mono text-green-400 text-xs font-bold mb-1">{SOURCE_LABEL[result.source] || result.source}</p>
                <p className="font-mono text-white text-lg font-bold">{result.shelter.name}</p>
                <p className="font-mono text-gray-500 text-xs mt-1">
                  {result.shelter.current_occupancy}/{result.shelter.capacity} occupied
                  {result.distance_km != null && ` // ${result.distance_km.toFixed(1)} km away`}
                </p>
              </div>

              <EvacuationMap
                zones={[myZone]}
                shelters={[result.shelter]}
                directionLine={
                  myZone.center_lat != null && result.shelter.lat != null
                    ? {
                        from: { lat: myZone.center_lat, lon: myZone.center_lon },
                        to: { lat: result.shelter.lat, lon: result.shelter.lon },
                        label: `${myZone.name} to ${result.shelter.name}`,
                      }
                    : null
                }
                height="50vh"
              />
            </>
          )}
        </>
      )}
    </div>
  )
}
