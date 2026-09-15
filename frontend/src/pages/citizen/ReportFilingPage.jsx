import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'

export default function ReportFilingPage() {
  const [zones, setZones] = useState([])
  const [selectedZoneId, setSelectedZoneId] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
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

  async function handleSubmit(e) {
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

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Report Filing</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        <div className="border border-gray-800 bg-surface-panel p-6 max-w-md">
          {submitted ? (
            <p className="font-mono text-green-400 text-xs">Report submitted. Thank you.</p>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
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
      )}
    </div>
  )
}
