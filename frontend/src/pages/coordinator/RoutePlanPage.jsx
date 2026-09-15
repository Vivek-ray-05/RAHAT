import { useState, useEffect, useCallback } from 'react'
import { useSocket } from '../../context/SocketContext'
import { api } from '../../api/client'
import EvacuationMap from '../../components/EvacuationMap'

export default function RoutePlanPage() {
  const { connect, disconnect } = useSocket()

  const [zones, setZones] = useState([])
  const [shelters, setShelters] = useState([])
  const [roads, setRoads] = useState([])
  const [runs, setRuns] = useState([])
  const [selectedRunId, setSelectedRunId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [zonesData, sheltersData, roadsData, runsData] = await Promise.all([
        api.get('/zones'),
        api.get('/shelters'),
        api.get('/roads'),
        api.get('/simulation'),
      ])
      setZones(zonesData)
      setShelters(sheltersData)
      setRoads(roadsData)
      setRuns(runsData)
      // Default to the running run if there is one, else the most
      // recently started run (runsData is already newest-first) --
      // "most recent" has to be resolved to a concrete id here since
      // EvacuationMap only fetches a route layer when given one.
      const defaultRun = runsData.find((r) => r.status === 'running') || runsData[0]
      if (defaultRun) setSelectedRunId(String(defaultRun.id))
    } catch (err) {
      setError(err.message || 'Could not load route plan data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (selectedRunId) connect(Number(selectedRunId))
    return () => disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRunId])

  async function handleBlockRoad(roadId) {
    try {
      await api.post(`/roads/${roadId}/block`, { reason: 'Blocked from Route Plan map' })
      const roadsData = await api.get('/roads')
      setRoads(roadsData)
    } catch (err) {
      setError(err.message || 'Could not block road')
    }
  }

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Route Plan</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        <>
          <div className="flex items-center gap-3 mb-4">
            <span className="font-mono text-xs text-gray-500">SHOWING_ROUTES_FOR</span>
            <select
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-xs px-3 py-2 outline-none"
            >
              {runs.length === 0 && <option value="" className="bg-black">NO_RUNS_YET</option>}
              {runs.map((r) => (
                <option key={r.id} value={r.id} className="bg-black">
                  RUN_{r.id} // {r.scenario_name} // {r.status}
                </option>
              ))}
            </select>
          </div>

          <EvacuationMap
            zones={zones}
            shelters={shelters}
            roads={roads}
            simulationRunId={selectedRunId ? Number(selectedRunId) : null}
            onBlockRoad={handleBlockRoad}
            height="70vh"
          />
        </>
      )}
    </div>
  )
}
