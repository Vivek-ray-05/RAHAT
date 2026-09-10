import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

const STATUS_COLOR = {
  executed: 'text-green-400 border-green-500/40',
  approved: 'text-green-400 border-green-500/40',
  modified: 'text-amber-400 border-amber-500/40',
  rejected: 'text-red-400 border-red-500/40',
  expired: 'text-gray-500 border-gray-600',
  pending_review: 'text-gray-400 border-gray-600',
}

export default function PostEventReportPage() {
  const { runId } = useParams()
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.get(`/reports/${runId}`)
      setReport(data)
    } catch (err) {
      setError(err.message || 'Could not load report')
    } finally {
      setLoading(false)
    }
  }, [runId])

  useEffect(() => {
    load()
  }, [load])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] hero-grid text-white p-8">
      <div className="flex justify-between items-start mb-10">
        <div>
          <p className="font-mono text-green-500 text-xs tracking-widest mb-2 opacity-70">
            POST_EVENT_REPORT // RUN_{runId}
          </p>
          <h1 className="font-mono font-bold text-3xl">Simulation Report</h1>
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

      {!loading && report && (
        <div className="flex flex-col gap-6 max-w-5xl">
          <div className="border border-gray-800 bg-surface-panel p-6">
            <p className="font-mono text-green-400 text-sm font-bold mb-4">RUN_SUMMARY</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs text-gray-400">
              <div>
                <div className="text-gray-600">SCENARIO</div>
                <div className="text-gray-300 mt-1">{report.scenario_name}</div>
              </div>
              <div>
                <div className="text-gray-600">STATUS</div>
                <div className="text-gray-300 mt-1 uppercase">{report.status}</div>
              </div>
              <div>
                <div className="text-gray-600">STARTED_BY</div>
                <div className="text-gray-300 mt-1">{report.started_by_name || 'unknown'}</div>
              </div>
              <div>
                <div className="text-gray-600">TICKS_RUN</div>
                <div className="text-gray-300 mt-1">{report.tick_count}</div>
              </div>
            </div>
            <div className="flex gap-4 mt-4 flex-wrap">
              {Object.entries(report.status_counts).map(([status, count]) => (
                <span
                  key={status}
                  className={`font-mono text-xs border px-2 py-1 uppercase ${STATUS_COLOR[status] || 'text-gray-400 border-gray-700'}`}
                >
                  {status}: {count}
                </span>
              ))}
              {Object.keys(report.status_counts).length === 0 && (
                <span className="font-mono text-xs text-gray-600">No recommendations were generated in this run.</span>
              )}
            </div>
          </div>

          <div className="border border-gray-800 bg-surface-panel p-6">
            <p className="font-mono text-amber-400 text-sm font-bold mb-4">
              RECOMMENDATIONS // {report.recommendations.length}
            </p>
            <div className="flex flex-col gap-3">
              {report.recommendations.map((rec) => (
                <div key={rec.id} className="border-b border-gray-800 pb-3">
                  <div className="flex justify-between items-start">
                    <p className="font-mono text-green-400 text-xs font-bold">
                      {rec.zone_name || `Zone ${rec.zone_id}`}
                    </p>
                    <span className={`font-mono text-xs border px-2 py-1 uppercase ${STATUS_COLOR[rec.status] || 'text-gray-400 border-gray-700'}`}>
                      {rec.status}
                    </span>
                  </div>
                  {rec.reason && <p className="font-mono text-gray-500 text-xs mt-1">{rec.reason}</p>}
                  {rec.review && (
                    <p className="font-mono text-gray-600 text-xs mt-1">
                      {rec.review.action.toUpperCase()} by {rec.review.reviewed_by_name || 'unknown'}
                      {rec.review.reason ? ` -- "${rec.review.reason}"` : ''}
                    </p>
                  )}
                  {!rec.review && (
                    <p className="font-mono text-gray-700 text-xs mt-1">Never reviewed.</p>
                  )}
                </div>
              ))}
              {report.recommendations.length === 0 && (
                <p className="font-mono text-gray-500 text-xs">No recommendations to show for this run.</p>
              )}
            </div>
          </div>

          <div className="border border-gray-800 bg-surface-panel p-6">
            <p className="font-mono text-green-400 text-sm font-bold mb-4">
              AUDIT_TRAIL // {report.audit_trail.length}
            </p>
            <div className="flex flex-col gap-1 max-h-96 overflow-y-auto">
              {report.audit_trail.map((event) => (
                <p key={event.id} className="font-mono text-xs text-gray-500">
                  <span className="text-gray-700">{event.created_at}</span>
                  {' // '}
                  <span className="text-gray-300">{event.event_type}</span>
                  {' // by '}
                  {event.actor_name || 'system'}
                </p>
              ))}
              {report.audit_trail.length === 0 && (
                <p className="font-mono text-gray-500 text-xs">No audit events recorded for this run yet.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
