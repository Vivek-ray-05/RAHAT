import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { SocketProvider, useSocket } from './SocketContext'

class FakeWebSocket {
  static instances = []

  constructor(url) {
    this.url = url
    this.onopen = null
    this.onclose = null
    this.onerror = null
    this.onmessage = null
    this.closed = false
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.closed = true
    this.onclose?.()
  }
}

describe('SocketContext', () => {
  beforeEach(() => {
    sessionStorage.clear()
    FakeWebSocket.instances = []
    vi.stubGlobal('WebSocket', FakeWebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('refuses to connect without a stored auth token', () => {
    const { result } = renderHook(() => useSocket(), { wrapper: SocketProvider })

    act(() => {
      result.current.connect(7)
    })

    expect(result.current.error).toMatch(/not authenticated/i)
    expect(FakeWebSocket.instances).toHaveLength(0)
  })

  it('connects with the run id and token in the WS url', () => {
    sessionStorage.setItem('rahat_token', 'jwt-live')
    const { result } = renderHook(() => useSocket(), { wrapper: SocketProvider })

    act(() => {
      result.current.connect(42)
    })

    expect(FakeWebSocket.instances).toHaveLength(1)
    expect(FakeWebSocket.instances[0].url).toContain('/simulation/42/ws?token=jwt-live')
  })

  it('marks connected once the socket opens', async () => {
    sessionStorage.setItem('rahat_token', 'jwt-live')
    const { result } = renderHook(() => useSocket(), { wrapper: SocketProvider })

    act(() => {
      result.current.connect(1)
    })
    act(() => {
      FakeWebSocket.instances[0].onopen()
    })

    await waitFor(() => expect(result.current.connected).toBe(true))
  })

  it('parses an incoming tick message', async () => {
    sessionStorage.setItem('rahat_token', 'jwt-live')
    const { result } = renderHook(() => useSocket(), { wrapper: SocketProvider })

    act(() => {
      result.current.connect(1)
    })
    act(() => {
      FakeWebSocket.instances[0].onmessage({ data: JSON.stringify({ tick_number: 3, timestamp: '2026-09-10T00:00:00Z' }) })
    })

    await waitFor(() => expect(result.current.latestTick).toEqual({ tick_number: 3, timestamp: '2026-09-10T00:00:00Z' }))
  })

  it('ignores a malformed frame instead of crashing', () => {
    sessionStorage.setItem('rahat_token', 'jwt-live')
    const { result } = renderHook(() => useSocket(), { wrapper: SocketProvider })

    act(() => {
      result.current.connect(1)
    })

    expect(() => {
      act(() => {
        FakeWebSocket.instances[0].onmessage({ data: 'not json' })
      })
    }).not.toThrow()
    expect(result.current.latestTick).toBeNull()
  })

  it('disconnect closes the socket and resets connected state', async () => {
    sessionStorage.setItem('rahat_token', 'jwt-live')
    const { result } = renderHook(() => useSocket(), { wrapper: SocketProvider })

    act(() => {
      result.current.connect(1)
    })
    act(() => {
      FakeWebSocket.instances[0].onopen()
    })
    await waitFor(() => expect(result.current.connected).toBe(true))

    act(() => {
      result.current.disconnect()
    })

    expect(FakeWebSocket.instances[0].closed).toBe(true)
    expect(result.current.connected).toBe(false)
  })

  describe('auto-reconnect on an unexpected drop', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => vi.useRealTimers())

    it('opens a new socket after the server closes the connection unexpectedly', async () => {
      sessionStorage.setItem('rahat_token', 'jwt-live')
      const { result } = renderHook(() => useSocket(), { wrapper: SocketProvider })

      act(() => {
        result.current.connect(1)
      })
      act(() => {
        FakeWebSocket.instances[0].onopen()
      })
      expect(FakeWebSocket.instances).toHaveLength(1)

      // The server drops the connection -- not a disconnect() call --
      // so this should be treated as unexpected and retried.
      act(() => {
        FakeWebSocket.instances[0].onclose()
      })
      expect(result.current.connected).toBe(false)

      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000)
      })

      expect(FakeWebSocket.instances).toHaveLength(2)
      expect(FakeWebSocket.instances[1].url).toContain('/simulation/1/ws?token=jwt-live')
    })

    it('does not reconnect after a deliberate disconnect()', async () => {
      sessionStorage.setItem('rahat_token', 'jwt-live')
      const { result } = renderHook(() => useSocket(), { wrapper: SocketProvider })

      act(() => {
        result.current.connect(1)
      })
      act(() => {
        FakeWebSocket.instances[0].onopen()
      })

      act(() => {
        result.current.disconnect()
      })

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000)
      })

      expect(FakeWebSocket.instances).toHaveLength(1)
    })

    it('gives up with a clear message after the max reconnect attempts', async () => {
      sessionStorage.setItem('rahat_token', 'jwt-live')
      const { result } = renderHook(() => useSocket(), { wrapper: SocketProvider })

      act(() => {
        result.current.connect(1)
      })

      // 5 drops each schedule and open a retry (1 initial + 5 retries = 6 sockets).
      for (let i = 0; i < 5; i++) {
        const latest = FakeWebSocket.instances[FakeWebSocket.instances.length - 1]
        act(() => {
          latest.onclose()
        })
        await act(async () => {
          await vi.advanceTimersByTimeAsync(2000)
        })
      }
      expect(FakeWebSocket.instances).toHaveLength(6)

      // The 6th drop is the one that finally exhausts the attempt budget --
      // no further socket gets opened, and the error becomes terminal.
      const sixth = FakeWebSocket.instances[FakeWebSocket.instances.length - 1]
      act(() => {
        sixth.onclose()
      })
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000)
      })

      expect(result.current.error).toMatch(/lost connection.*click watch/i)
      expect(FakeWebSocket.instances).toHaveLength(6)
    })
  })
})
