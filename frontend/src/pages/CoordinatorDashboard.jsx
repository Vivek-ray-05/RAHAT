import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function CoordinatorDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [zones, setZones] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [zonesData, recsData] = await Promise.all([
        api.get('/zones'),
        api.get('/recommendations'),
      ])
      setZones(zonesData)
      setRecommendations(recsData)
    } catch (err) {
      setError(err.message || 'Could not load city data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const highRiskZones = zones.filter((z) => (z.flood_risk_base ?? 0) >= 5)

  return (
    <div className="min-h-screen bg-[#0a0a0a] hero-grid text-white p-8">
      <div className="flex justify-between items-start mb-10">
        <div>
          <p className="font-mono text-green-500 text-xs tracking-widest mb-2 opacity-70">
            CENTRAL_COORDINATOR // SESSION_ACTIVE
          </p>
          <h1 className="font-mono font-bold text-3xl">Coordinator Dashboard</h1>
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

      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-5xl">
          <div className="border border-gray-800 bg-surface-panel p-6">
            <p className="font-mono text-green-400 text-sm font-bold mb-4">
              CITY_OVERVIEW // {zones.length} ZONES
            </p>
            <p className="font-mono text-gray-500 text-xs mb-3">
              {highRiskZones.length} zone(s) with elevated baseline flood risk
            </p>
            <div className="flex flex-col gap-2 max-h-80 overflow-y-auto">
              {zones.map((z) => (
                <div key={z.id} className="flex justify-between font-mono text-xs text-gray-400 border-b border-gray-800 pb-1">
                  <span>{z.name}</span>
                  <span className="text-gray-600">
                    pop {z.population.toLocaleString()} // {z.elevation_tier}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-gray-800 bg-surface-panel p-6">
            <p className="font-mono text-amber-400 text-sm font-bold mb-4">
              PENDING_APPROVALS // {recommendations.length}
            </p>
            {recommendations.length === 0 && (
              <p className="font-mono text-gray-500 text-xs">
                No pending recommendations across any zone right now.
              </p>
            )}
            <div className="flex flex-col gap-3">
              {recommendations.map((rec) => (
                <div key={rec.id} className="font-mono text-xs text-gray-400 border-b border-gray-800 pb-2">
                  <p className="text-green-400">{rec.payload_json.zone_name}</p>
                  <p className="text-gray-600">{rec.payload_json.reason}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
