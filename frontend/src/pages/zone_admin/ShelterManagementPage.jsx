import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../api/client'

export default function ShelterManagementPage() {
  const { user } = useAuth()

  const [shelters, setShelters] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editValue, setEditValue] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setShelters(await api.get(`/shelters?zone_id=${user?.zone_id}`))
    } catch (err) {
      setError(err.message || 'Could not load shelters')
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => { load() }, [load])

  function startEdit(shelter) {
    setEditingId(shelter.id)
    setEditValue(String(shelter.current_occupancy))
  }

  async function handleSave(shelter) {
    setSaving(true)
    setError('')
    try {
      await api.patch(`/shelters/${shelter.id}`, { current_occupancy: Number(editValue) })
      setEditingId(null)
      await load()
    } catch (err) {
      setError(err.message || 'Could not update occupancy')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="text-white">
      <h1 className="font-mono font-bold text-2xl mb-6">Shelter Management</h1>

      {error && <p className="font-mono text-red-400 text-xs tracking-widest mb-4">{`ERROR: ${error}`}</p>}
      {loading && <p className="font-mono text-gray-500 text-sm">LOADING...</p>}

      {!loading && (
        <div className="flex flex-col gap-3 max-w-2xl">
          {shelters.length === 0 && (
            <p className="font-mono text-gray-500 text-xs">No shelters in your zone yet.</p>
          )}
          {shelters.map((s) => (
            <div key={s.id} className="border border-gray-800 bg-surface-panel p-4 flex justify-between items-center">
              <div>
                <p className="font-mono text-green-400 text-sm">{s.name}</p>
                <p className="font-mono text-gray-600 text-xs mt-1">capacity {s.capacity}</p>
              </div>
              {editingId === s.id ? (
                <div className="flex gap-2 items-center">
                  <input
                    type="number"
                    min="0"
                    max={s.capacity}
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    className="w-24 bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-xs px-2 py-1 outline-none"
                  />
                  <button
                    onClick={() => handleSave(s)}
                    disabled={saving}
                    className="font-mono text-xs text-green-400 border border-green-500/50 px-2 py-1 hover:bg-green-500/10 disabled:opacity-40"
                  >
                    SAVE
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    disabled={saving}
                    className="font-mono text-xs text-gray-400 border border-gray-600 px-2 py-1 hover:bg-gray-500/10 disabled:opacity-40"
                  >
                    CANCEL
                  </button>
                </div>
              ) : (
                <div className="flex gap-3 items-center">
                  <span className="font-mono text-white text-lg font-bold">{s.current_occupancy}/{s.capacity}</span>
                  <button
                    onClick={() => startEdit(s)}
                    className="font-mono text-xs text-amber-400 border border-amber-500/50 px-2 py-1 hover:bg-amber-500/10"
                  >
                    EDIT
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
