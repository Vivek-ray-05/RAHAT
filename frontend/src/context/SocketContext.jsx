import { createContext, useContext, useState, useCallback, useRef } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL
const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECT_ATTEMPTS = 5
const SocketContext = createContext(null)

export function SocketProvider({ children }) {
  const [connected, setConnected] = useState(false)
  const [latestTick, setLatestTick] = useState(null)
  const [error, setError] = useState('')
  const socketRef = useRef(null)
  const runIdRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const attemptsRef = useRef(0)

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimerRef.current)
    runIdRef.current = null
    socketRef.current?.close()
    socketRef.current = null
    setConnected(false)
  }, [])

  // A real deploy or a brief network drop closes the socket out from
  // under an actively-watching user -- found live (a coordinator's
  // WATCH connection died mid-deploy and never came back without a
  // manual re-click). This retries a few times on its own before
  // giving up, instead of leaving a dead connection with a cryptic
  // error as the only feedback.
  const openSocket = useCallback((runId) => {
    const token = sessionStorage.getItem('rahat_token')
    if (!token) {
      setError('Not authenticated')
      return
    }

    const ws = new WebSocket(`${WS_URL}/simulation/${runId}/ws?token=${token}`)

    ws.onopen = () => {
      attemptsRef.current = 0
      setError('')
      setConnected(true)
    }
    ws.onclose = () => {
      setConnected(false)
      if (socketRef.current !== ws) return // already superseded by a newer connection
      socketRef.current = null

      // runIdRef is only still set to this run if nobody called
      // disconnect() (which clears it first) -- so this branch means
      // the drop was unexpected, not a deliberate navigation-away.
      if (runIdRef.current !== runId) return

      if (attemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
        setError('Lost connection to the live tick stream. Click WATCH to try again.')
        return
      }
      attemptsRef.current += 1
      setError(`Connection dropped, reconnecting (${attemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})...`)
      reconnectTimerRef.current = setTimeout(() => openSocket(runId), RECONNECT_DELAY_MS)
    }
    ws.onerror = () => {
      // onclose always follows onerror for a WebSocket -- the retry
      // logic lives there so it only runs once per drop.
    }
    ws.onmessage = (event) => {
      try {
        setLatestTick(JSON.parse(event.data))
      } catch {
        // ignore a malformed frame, keep the connection alive
      }
    }

    socketRef.current = ws
  }, [])

  const connect = useCallback((runId) => {
    disconnect()
    setError('')
    setLatestTick(null)
    attemptsRef.current = 0
    runIdRef.current = runId
    openSocket(runId)
  }, [disconnect, openSocket])

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
