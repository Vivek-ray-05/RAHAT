import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function NDRFDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [zone, setZone] = useState(null)
  const [route, setRoute] = useState(null)
  const [shelter, setShelter] = useState(null)
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
      const zones = await api.get('/zones')
      setZone(zones.find((z) => z.id === user.zone_id) || null)

      try {
        const routeData = await api.get(`/zones/${user.zone_id}/routes`)
        setRoute(routeData)
        const shelters = await api.get('/shelters')
        setShelter(shelters.find((s) => s.id === routeData.to_shelter_id) || null)
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

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] hero-grid text-white p-8">
      <div className="flex justify-between items-start mb-10">
        <div>
          <p className="font-mono text-green-500 text-xs tracking-widest mb-2 opacity-70">
            NDRF // SESSION_ACTIVE
          </p>
          <h1 className="font-mono font-bold text-3xl">Response Dashboard</h1>
          <p className="font-mono text-gray-500 text-xs mt-2">USER_ID: {user?.id}</p>
        </div>
        <button
          onClick={handleLogout}
          className="font-mono text-red-400 text-xs tracking-widest border border-red-500/50 px-4 py-2 hover:bg-red-500/10 transition-all"
        >
          LOGOUT
        </button>
      </div>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-6">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && !user?.zone_id && (
        <div className="border border-gray-800 bg-surface-panel p-8 max-w-2xl">
          <p className="font-mono text-gray-400 text-sm">
            No zone assignment on this account yet.
          </p>
        </div>
      )}

      {!loading && user?.zone_id && (
        <div className="max-w-2xl border border-gray-800 bg-surface-panel p-6">
          <p className="font-mono text-green-400 text-sm font-bold mb-4">
            ASSIGNED_ZONE // {zone?.name || `Zone ${user.zone_id}`}
          </p>

          {!route && (
            <p className="font-mono text-gray-500 text-xs">
              No evacuation route computed for this zone yet.
            </p>
          )}

          {route && (
            <div className="font-mono text-xs text-gray-400 flex flex-col gap-2">
              <p>
                ROUTE_STATUS // <span className="text-amber-400">{route.status}</span>
              </p>
              <p>
                TARGET_SHELTER // {shelter?.name || `Shelter ${route.to_shelter_id}`}
              </p>
              <p>ETA // {route.eta} min</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
