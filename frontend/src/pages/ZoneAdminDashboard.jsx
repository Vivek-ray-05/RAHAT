import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function ZoneAdminDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actingOn, setActingOn] = useState(null)

  const loadRecommendations = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.get('/recommendations')
      setRecommendations(data)
    } catch (err) {
      setError(err.message || 'Could not load recommendations')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRecommendations()
  }, [loadRecommendations])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  async function handleApprove(id) {
    setActingOn(id)
    try {
      await api.post(`/recommendations/${id}/approve`)
      await loadRecommendations()
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
      await loadRecommendations()
    } catch (err) {
      setError(err.message || 'Reject failed')
    } finally {
      setActingOn(null)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] hero-grid text-white p-8">
      <div className="flex justify-between items-start mb-10">
        <div>
          <p className="font-mono text-green-500 text-xs tracking-widest mb-2 opacity-70">
            ZONE_ADMIN // SESSION_ACTIVE
          </p>
          <h1 className="font-mono font-bold text-3xl">Recommendation Queue</h1>
          <p className="font-mono text-gray-500 text-xs mt-2">USER_ID: {user?.id}</p>
        </div>
        <button
          onClick={handleLogout}
          className="font-mono text-red-400 text-xs tracking-widest border border-red-500/50 px-4 py-2 hover:bg-red-500/10 transition-all"
        >
          LOGOUT
        </button>
      </div>

      {error && (
        <p className="font-mono text-red-400 text-xs tracking-widest mb-6">{`ERROR: ${error}`}</p>
      )}

      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && recommendations.length === 0 && (
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
            <div className="flex gap-3">
              <button
                onClick={() => handleApprove(rec.id)}
                disabled={actingOn === rec.id}
                className="font-mono text-green-400 text-xs tracking-widest border border-green-500 px-4 py-2 hover:bg-green-500/10 disabled:opacity-40"
              >
                {actingOn === rec.id ? 'WORKING...' : 'APPROVE'}
              </button>
              <button
                onClick={() => handleReject(rec.id)}
                disabled={actingOn === rec.id}
                className="font-mono text-red-400 text-xs tracking-widest border border-red-500/50 px-4 py-2 hover:bg-red-500/10 disabled:opacity-40"
              >
                REJECT
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
