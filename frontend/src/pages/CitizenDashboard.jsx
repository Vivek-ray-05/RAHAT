import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function CitizenDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [zones, setZones] = useState([])
  const [shelters, setShelters] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [selectedZoneId, setSelectedZoneId] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [zonesData, sheltersData] = await Promise.all([api.get('/zones'), api.get('/shelters')])
      setZones(zonesData)
      setShelters(sheltersData)
    } catch (err) {
      setError(err.message || 'Could not load data')
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

  async function handleSubmitReport(e) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await api.post('/citizen-reports', { zone_id: Number(selectedZoneId), description })
      setSubmitted(true)
      setDescription('')
    } catch (err) {
      setError(err.message || 'Could not submit report')
    } finally {
      setSubmitting(false)
    }
  }

  const zoneName = (id) => zones.find((z) => z.id === id)?.name || `Zone ${id}`

  return (
    <div className="min-h-screen bg-[#0a0a0a] hero-grid text-white p-8">
      <div className="flex justify-between items-start mb-10">
        <div>
          <p className="font-mono text-green-500 text-xs tracking-widest mb-2 opacity-70">
            CITIZEN // SESSION_ACTIVE
          </p>
          <h1 className="font-mono font-bold text-3xl">Citizen Portal</h1>
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
              SHELTERS // {shelters.length}
            </p>
            <div className="flex flex-col gap-2 max-h-80 overflow-y-auto">
              {shelters.map((s) => (
                <div key={s.id} className="font-mono text-xs text-gray-400 border-b border-gray-800 pb-1">
                  <p className="text-gray-300">{s.name}</p>
                  <p className="text-gray-600">
                    {zoneName(s.zone_id)} // {s.current_occupancy}/{s.capacity}
                    {s.has_medical ? ' // MEDICAL' : ''}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-gray-800 bg-surface-panel p-6">
            <p className="font-mono text-amber-400 text-sm font-bold mb-4">SUBMIT_INCIDENT_REPORT</p>
            {submitted ? (
              <p className="font-mono text-green-400 text-xs">Report submitted. Thank you.</p>
            ) : (
              <form onSubmit={handleSubmitReport} className="flex flex-col gap-3">
                <select
                  value={selectedZoneId}
                  onChange={(e) => setSelectedZoneId(e.target.value)}
                  required
                  className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-xs px-3 py-2 outline-none"
                >
                  <option value="" className="bg-black">SELECT ZONE</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id} className="bg-black">{z.name}</option>
                  ))}
                </select>
                <textarea
                  placeholder="DESCRIBE WHAT YOU'RE SEEING"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  rows={4}
                  className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-xs px-3 py-2 outline-none placeholder:text-gray-600"
                />
                <button
                  type="submit"
                  disabled={submitting}
                  className="font-mono text-amber-400 text-xs tracking-widest border border-amber-500 px-4 py-2 hover:bg-amber-500/10 disabled:opacity-40"
                >
                  {submitting ? 'SUBMITTING...' : 'SUBMIT'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
