import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../api/client'
import EvacuationMap from '../../components/EvacuationMap'

export default function RoutePlanningPage() {
  const { user } = useAuth()

  const [recommendations, setRecommendations] = useState([])
  const [shelters, setShelters] = useState([])
  const [myZone, setMyZone] = useState(null)
  const [roads, setRoads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actingOn, setActingOn] = useState(null)

  const [modifyingId, setModifyingId] = useState(null)
  const [modifiedShelterId, setModifiedShelterId] = useState('')
  const [modifiedPopulation, setModifiedPopulation] = useState('')
  const [modifyReason, setModifyReason] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [recsData, sheltersData, zonesData, roadsData] = await Promise.all([
        api.get('/recommendations'),
        api.get('/shelters'),
        api.get('/zones'),
        api.get('/roads'),
      ])
      setRecommendations(recsData)
      setShelters(sheltersData)
      setMyZone(zonesData.find((z) => z.id === user?.zone_id) || null)
      setRoads(roadsData.filter((r) => r.from_zone_id === user?.zone_id || r.to_zone_id === user?.zone_id))
    } catch (err) {
      setError(err.message || 'Could not load recommendations')
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => { load() }, [load])

  async function handleApprove(id) {
    setActingOn(id)
    try {
      await api.post(`/recommendations/${id}/approve`)
      await load()
    } catch (err) {
      setError(err.message || 'Approve failed')
    } finally {
      setActingOn(null)
    }
  }

  async function handleReject(id) {
    setActingOn(id)
    try {
      await api.post(`/recommendations/${id}/reject`, { reason: 'Rejected by zone admin' })
      await load()
    } catch (err) {
      setError(err.message || 'Reject failed')
    } finally {
      setActingOn(null)
    }
  }

  function startModify(rec) {
    setModifyingId(rec.id)
    setModifiedShelterId(rec.payload_json.assigned_shelter_id ?? '')
    setModifiedPopulation(rec.payload_json.assigned_population ?? 0)
    setModifyReason('')
  }

  async function handleModifySubmit(rec) {
    setActingOn(rec.id)
    try {
      const modified_payload = {
        ...rec.payload_json,
        assigned_shelter_id: modifiedShelterId ? Number(modifiedShelterId) : null,
        assigned_population: Number(modifiedPopulation) || 0,
      }
      await api.post(`/recommendations/${rec.id}/modify`, {
        modified_payload,
        reason: modifyReason || undefined,
      })
      setModifyingId(null)
      await load()
    } catch (err) {
      setError(err.message || 'Modify failed')
    } finally {
      setActingOn(null)
    }
  }

  async function handleBlockRoad(roadId) {
    try {
      await api.post(`/roads/${roadId}/block`, { reason: 'Blocked from Route Planning map' })
      await load()
    } catch (err) {
      setError(err.message || 'Could not block road')
    }
  }

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Route Planning</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        <>
          <EvacuationMap
            zones={myZone ? [myZone] : []}
            shelters={shelters}
            roads={roads}
            onBlockRoad={handleBlockRoad}
            height="50vh"
          />

          <div className="mt-6">
            {recommendations.length === 0 && (
              <div className="border border-gray-800 bg-surface-panel p-8 max-w-2xl">
                <p className="font-mono text-gray-400 text-sm">
                  No pending recommendations. They appear here automatically when a running
                  simulation's risk crosses the replan threshold.
                </p>
              </div>
            )}

            <div className="flex flex-col gap-4 max-w-3xl">
              {recommendations.map((rec) => (
                <div key={rec.id} className="border border-gray-800 bg-surface-panel p-6">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <p className="font-mono text-green-400 text-sm font-bold">
                        {rec.payload_json.zone_name || `Zone ${rec.payload_json.zone_id}`}
                      </p>
                      <p className="font-mono text-gray-500 text-xs mt-1">
                        priority: {rec.payload_json.priority_score} // risk: {rec.payload_json.risk_score}
                      </p>
                    </div>
                    <span className="font-mono text-xs text-amber-400 border border-amber-500/40 px-2 py-1">
                      {rec.status.toUpperCase()}
                    </span>
                  </div>
                  <p className="font-mono text-gray-400 text-xs mb-4">{rec.payload_json.reason}</p>
                  <p className="font-mono text-gray-600 text-xs mb-4">
                    shelter: {rec.payload_json.assigned_shelter_id ?? 'none'} // population: {rec.payload_json.assigned_population ?? 0}
                  </p>

                  {modifyingId === rec.id ? (
                    <div className="flex flex-col gap-3 border-t border-gray-800 pt-4">
                      <select
                        value={modifiedShelterId}
                        onChange={(e) => setModifiedShelterId(e.target.value)}
                        className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-xs px-3 py-2 outline-none"
                      >
                        <option value="" className="bg-black">NO SHELTER</option>
                        {shelters.map((s) => (
                          <option key={s.id} value={s.id} className="bg-black">
                            {s.name} ({s.current_occupancy}/{s.capacity})
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        min="0"
                        value={modifiedPopulation}
                        onChange={(e) => setModifiedPopulation(e.target.value)}
                        placeholder="ASSIGNED POPULATION"
                        className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-xs px-3 py-2 outline-none"
                      />
                      <input
                        type="text"
                        value={modifyReason}
                        onChange={(e) => setModifyReason(e.target.value)}
                        placeholder="REASON FOR MODIFICATION (OPTIONAL)"
                        className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-xs px-3 py-2 outline-none placeholder:text-gray-600"
                      />
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleModifySubmit(rec)}
                          disabled={actingOn === rec.id}
                          className="font-mono text-amber-400 text-xs tracking-widest border border-amber-500 px-4 py-2 hover:bg-amber-500/10 disabled:opacity-40"
                        >
                          {actingOn === rec.id ? 'WORKING...' : 'SAVE_AND_APPROVE'}
                        </button>
                        <button
                          onClick={() => setModifyingId(null)}
                          disabled={actingOn === rec.id}
                          className="font-mono text-gray-400 text-xs tracking-widest border border-gray-600 px-4 py-2 hover:bg-gray-500/10 disabled:opacity-40"
                        >
                          CANCEL
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex gap-3">
                      <button
                        onClick={() => handleApprove(rec.id)}
                        disabled={actingOn === rec.id}
                        className="font-mono text-green-400 text-xs tracking-widest border border-green-500 px-4 py-2 hover:bg-green-500/10 disabled:opacity-40"
                      >
                        {actingOn === rec.id ? 'WORKING...' : 'APPROVE'}
                      </button>
                      <button
                        onClick={() => startModify(rec)}
                        disabled={actingOn === rec.id}
                        className="font-mono text-amber-400 text-xs tracking-widest border border-amber-500/50 px-4 py-2 hover:bg-amber-500/10 disabled:opacity-40"
                      >
                        MODIFY
                      </button>
                      <button
                        onClick={() => handleReject(rec.id)}
                        disabled={actingOn === rec.id}
                        className="font-mono text-red-400 text-xs tracking-widest border border-red-500/50 px-4 py-2 hover:bg-red-500/10 disabled:opacity-40"
                      >
                        REJECT
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
