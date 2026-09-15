import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../api/client'
import EvacuationMap from '../../components/EvacuationMap'

export default function NDRFPage() {
  const { user } = useAuth()

  const [zone, setZone] = useState(null)
  const [shelters, setShelters] = useState([])
  const [roads, setRoads] = useState([])
  const [reports, setReports] = useState([])
  const [route, setRoute] = useState(null)
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
      const [zonesData, sheltersData, roadsData, reportsData] = await Promise.all([
        api.get('/zones'),
        api.get('/shelters'),
        api.get('/roads'),
        api.get(`/citizen-reports?zone_id=${user.zone_id}`),
      ])
      setZone(zonesData.find((z) => z.id === user.zone_id) || null)
      setShelters(sheltersData)
      setRoads(roadsData.filter((r) => r.from_zone_id === user.zone_id || r.to_zone_id === user.zone_id))
      setReports(reportsData)

      try {
        setRoute(await api.get(`/zones/${user.zone_id}/routes`))
      } catch (err) {
        if (err.status !== 404) throw err
        setRoute(null)
      }
    } catch (err) {
      setError(err.message || 'Could not load zone data')
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => { load() }, [load])

  async function handleBlockRoad(roadId) {
    try {
      await api.post(`/roads/${roadId}/block`, { reason: 'Blocked by NDRF on scene' })
      const roadsData = await api.get('/roads')
      setRoads(roadsData.filter((r) => r.from_zone_id === user.zone_id || r.to_zone_id === user.zone_id))
    } catch (err) {
      setError(err.message || 'Could not block road')
    }
  }

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Response Dashboard</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && !user?.zone_id && (
        <div className="border border-gray-800 bg-surface-panel p-8 max-w-2xl">
          <p className="font-mono text-gray-400 text-sm">No zone assignment on this account yet.</p>
        </div>
      )}

      {!loading && user?.zone_id && (
        <>
          <div className="border border-gray-800 bg-surface-panel p-6 mb-6 max-w-2xl">
            <p className="font-mono text-green-400 text-sm font-bold mb-2">
              ASSIGNED_ZONE // {zone?.name || `Zone ${user.zone_id}`}
            </p>
            {!route && <p className="font-mono text-gray-500 text-xs">No evacuation route computed for this zone yet.</p>}
            {route && (
              <div className="font-mono text-xs text-gray-400 flex flex-col gap-1">
                <p>ROUTE_STATUS // <span className="text-amber-400">{route.status}</span></p>
                <p>ETA // {route.eta} min</p>
              </div>
            )}
          </div>

          <EvacuationMap zones={zone ? [zone] : []} shelters={shelters} roads={roads} onBlockRoad={handleBlockRoad} height="50vh" />

          <div className="border border-gray-800 bg-surface-panel p-6 mt-6 max-w-3xl">
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
