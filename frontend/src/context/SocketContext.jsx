import { createContext, useContext, useState, useCallback, useRef } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL
const SocketContext = createContext(null)

export function SocketProvider({ children }) {
  const [connected, setConnected] = useState(false)
  const [latestTick, setLatestTick] = useState(null)
  const [error, setError] = useState('')
  const socketRef = useRef(null)
  const runIdRef = useRef(null)

  const disconnect = useCallback(() => {
    socketRef.current?.close()
    socketRef.current = null
    runIdRef.current = null
    setConnected(false)
  }, [])

  const connect = useCallback((runId) => {
    disconnect()
    setError('')
    setLatestTick(null)

    const token = sessionStorage.getItem('rahat_token')
    if (!token) {
      setError('Not authenticated')
      return
    }

    const ws = new WebSocket(`${WS_URL}/simulation/${runId}/ws?token=${token}`)
    runIdRef.current = runId

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      if (socketRef.current === ws) socketRef.current = null
    }
    ws.onerror = () => setError('Connection to live tick stream failed')
    ws.onmessage = (event) => {
      try {
        setLatestTick(JSON.parse(event.data))
      } catch {
        // ignore a malformed frame, keep the connection alive
      }
    }

    socketRef.current = ws
  }, [disconnect])

  return (
    <SocketContext.Provider value={{ connect, disconnect, connected, latestTick, error }}>
      {children}
    </SocketContext.Provider>
  )
}

export function useSocket() {
  const ctx = useContext(SocketContext)
  if (!ctx) throw new Error('useSocket must be used within SocketProvider')
  return ctx
}
