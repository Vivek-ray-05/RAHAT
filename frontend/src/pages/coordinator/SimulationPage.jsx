import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSocket } from '../../context/SocketContext'
import { api } from '../../api/client'

const STATUS_COLOR = {
  running: 'text-green-400 border-green-500/40',
  paused: 'text-amber-400 border-amber-500/40',
  completed: 'text-gray-400 border-gray-600',
}

export default function SimulationPage() {
  const navigate = useNavigate()
  const { connect, disconnect, connected, latestTick, error: socketError } = useSocket()

  const [scenarios, setScenarios] = useState([])
  const [runs, setRuns] = useState([])
  const [selectedScenarioId, setSelectedScenarioId] = useState('')
  const [watchedRunId, setWatchedRunId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [acting, setActing] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [scenariosData, runsData] = await Promise.all([
        api.get('/scenarios'),
        api.get('/simulation'),
      ])
      setScenarios(scenariosData)
      setRuns(runsData)
    } catch (err) {
      setError(err.message || 'Could not load simulation data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => () => disconnect(), [disconnect])

  function watch(runId) {
    setWatchedRunId(runId)
    connect(runId)
  }

  async function handleStart() {
    if (!selectedScenarioId) return
    setActing(true)
    setError('')
    try {
      const run = await api.post('/simulation/start', { scenario_id: Number(selectedScenarioId) })
      await load()
      watch(run.id)
    } catch (err) {
      setError(err.message || 'Could not start simulation')
    } finally {
      setActing(false)
    }
  }

  async function handleAction(runId, action) {
    setActing(true)
    setError('')
    try {
      await api.post(`/simulation/${runId}/${action}`)
      await load()
    } catch (err) {
      setError(err.message || `Could not ${action} simulation`)
    } finally {
      setActing(false)
    }
  }

  async function handleTick(runId) {
    setActing(true)
    setError('')
    try {
      await api.post(`/simulation/${runId}/tick`)
    } catch (err) {
      setError(err.message || 'Could not advance tick')
    } finally {
      setActing(false)
    }
  }

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Simulation</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        <>
          <div className="border border-gray-800 bg-surface-panel p-6 mb-6 max-w-2xl">
            <p className="font-mono text-green-400 text-sm font-bold mb-4">START_NEW_RUN</p>
            <div className="flex gap-3">
              <select
                value={selectedScenarioId}
                onChange={(e) => setSelectedScenarioId(e.target.value)}
                className="flex-1 bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-xs px-3 py-2 outline-none"
              >
                <option value="" className="bg-black">SELECT SCENARIO</option>
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id} className="bg-black">{s.name}</option>
                ))}
              </select>
              <button
                onClick={handleStart}
                disabled={!selectedScenarioId || acting}
                className="font-mono text-green-400 text-xs tracking-widest border border-green-500 px-4 py-2 hover:bg-green-500/10 disabled:opacity-40"
              >
                START
              </button>
            </div>
          </div>

          <div className="border border-gray-800 bg-surface-panel p-6 mb-6 max-w-3xl">
            <p className="font-mono text-green-400 text-sm font-bold mb-4">RUNS // {runs.length}</p>
            {runs.length === 0 && (
              <p className="font-mono text-gray-500 text-xs">No simulation runs yet.</p>
            )}
            <div className="flex flex-col gap-3">
              {runs.map((run) => (
                <div key={run.id} className="border-b border-gray-800 pb-3 flex justify-between items-start">
                  <div>
                    <p className="font-mono text-xs text-gray-300">
                      RUN_{run.id} // {run.scenario_name}
                    </p>
                    <p className="font-mono text-xs text-gray-600 mt-1">
                      started by {run.started_by_name || 'unknown'} // {new Date(run.started_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`font-mono text-xs border px-2 py-1 uppercase ${STATUS_COLOR[run.status] || 'text-gray-400 border-gray-700'}`}>
                      {run.status}
                    </span>
                    {run.status === 'running' && (
                      <>
                        <button onClick={() => handleTick(run.id)} disabled={acting} className="font-mono text-xs text-green-400 border border-green-500/50 px-2 py-1 hover:bg-green-500/10 disabled:opacity-40">TICK</button>
                        <button onClick={() => handleAction(run.id, 'pause')} disabled={acting} className="font-mono text-xs text-amber-400 border border-amber-500/50 px-2 py-1 hover:bg-amber-500/10 disabled:opacity-40">PAUSE</button>
                        <button onClick={() => handleAction(run.id, 'complete')} disabled={acting} className="font-mono text-xs text-gray-400 border border-gray-600 px-2 py-1 hover:bg-gray-500/10 disabled:opacity-40">COMPLETE</button>
                      </>
                    )}
                    {run.status === 'paused' && (
                      <button onClick={() => handleAction(run.id, 'resume')} disabled={acting} className="font-mono text-xs text-green-400 border border-green-500/50 px-2 py-1 hover:bg-green-500/10 disabled:opacity-40">RESUME</button>
                    )}
                    {run.status === 'completed' && (
                      <button onClick={() => navigate(`/report/${run.id}`)} className="font-mono text-xs text-blue-400 border border-blue-500/50 px-2 py-1 hover:bg-blue-500/10">VIEW_REPORT</button>
                    )}
                    <button onClick={() => watch(run.id)} className="font-mono text-xs text-gray-400 border border-gray-600 px-2 py-1 hover:bg-gray-500/10">WATCH</button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-gray-800 bg-surface-panel p-6 max-w-3xl">
            <p className="font-mono text-green-400 text-sm font-bold mb-4">
              LIVE_TICK_STREAM // {watchedRunId ? `RUN_${watchedRunId}` : 'NONE'} // {connected ? 'CONNECTED' : 'DISCONNECTED'}
            </p>
            {socketError && <p className="font-mono text-red-400 text-xs mb-2">{`ERROR: ${socketError}`}</p>}
            {latestTick ? (
              <p className="font-mono text-gray-400 text-xs">
                tick {latestTick.tick_number} // {latestTick.timestamp}
              </p>
            ) : (
              <p className="font-mono text-gray-500 text-xs">
                No tick received yet. Click WATCH on a run above.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
