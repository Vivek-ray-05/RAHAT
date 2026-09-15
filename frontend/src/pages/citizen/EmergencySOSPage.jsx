import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'

const DEFAULT_SOS_MESSAGE = 'SOS -- immediate help needed'

export default function EmergencySOSPage() {
  const [zones, setZones] = useState([])
  const [selectedZoneId, setSelectedZoneId] = useState('')
  const [note, setNote] = useState(DEFAULT_SOS_MESSAGE)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
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

  async function handleSend(e) {
    e.preventDefault()
    setSending(true)
    setError('')
    try {
      await api.post('/citizen-reports', {
        zone_id: Number(selectedZoneId),
        description: note || DEFAULT_SOS_MESSAGE,
        is_sos: true,
      })
      setSent(true)
    } catch (err) {
      setError(err.message || 'Could not send SOS')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6 text-red-400">Emergency SOS</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        sent ? (
          <div className="border border-red-500 bg-red-500/10 p-8 max-w-md">
            <p className="font-mono text-red-400 text-lg font-bold mb-2">SOS SENT</p>
            <p className="font-mono text-gray-300 text-xs">
              Your emergency report has been sent to NDRF and your zone admin. Stay safe.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSend} className="border border-red-500/50 bg-surface-panel p-6 max-w-md flex flex-col gap-4">
            <select
              value={selectedZoneId}
              onChange={(e) => setSelectedZoneId(e.target.value)}
              required
              className="bg-transparent border border-gray-700 focus:border-red-500 text-red-400 font-mono text-xs px-3 py-2 outline-none"
            >
              <option value="" className="bg-black">SELECT YOUR ZONE</option>
              {zones.map((z) => (
                <option key={z.id} value={z.id} className="bg-black">{z.name}</option>
              ))}
            </select>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              className="bg-transparent border border-gray-700 focus:border-red-500 text-red-400 font-mono text-xs px-3 py-2 outline-none"
            />
            <button
              type="submit"
              disabled={!selectedZoneId || sending}
              className="font-mono text-white text-sm tracking-widest bg-red-600 border border-red-500 px-4 py-4 hover:bg-red-500 disabled:opacity-40"
            >
              {sending ? 'SENDING...' : 'SEND SOS'}
            </button>
          </form>
        )
      )}
    </div>
  )
}
