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
})
