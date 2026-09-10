import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { AuthProvider, useAuth } from './AuthContext'
import { api, setToken } from '../api/client'

vi.mock('../api/client', () => ({
  api: { post: vi.fn() },
  setToken: vi.fn(),
}))

describe('AuthContext', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.clearAllMocks()
  })

  it('starts with no user when sessionStorage is empty', () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    expect(result.current.user).toBeNull()
  })

  it('restores a persisted user from sessionStorage on mount', () => {
    sessionStorage.setItem('rahat_user', JSON.stringify({ id: 7, role: 'zone_admin', zone_id: 2 }))

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

    expect(result.current.user).toEqual({ id: 7, role: 'zone_admin', zone_id: 2 })
  })

  it('loginWithPassword sets the token and persists the returned user', async () => {
    api.post.mockResolvedValue({ access_token: 'jwt-abc', user_id: 1, role: 'central_coordinator', zone_id: null })
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

    await act(async () => {
      await result.current.loginWithPassword('a@rahat.dev', 'pw', 'central_coordinator')
    })

    expect(api.post).toHaveBeenCalledWith('/auth/login', { email: 'a@rahat.dev', password: 'pw', role: 'central_coordinator' })
    expect(setToken).toHaveBeenCalledWith('jwt-abc')
    expect(result.current.user).toEqual({ id: 1, role: 'central_coordinator', zone_id: null })
    expect(JSON.parse(sessionStorage.getItem('rahat_user'))).toEqual({ id: 1, role: 'central_coordinator', zone_id: null })
  })

  it('verifyOtp sets the token and persists the returned user', async () => {
    api.post.mockResolvedValue({ access_token: 'jwt-otp', user_id: 4, role: 'citizen', zone_id: 3 })
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

    await act(async () => {
      await result.current.verifyOtp('9110001111', '1234')
    })

    expect(api.post).toHaveBeenCalledWith('/auth/otp/verify', { phone: '9110001111', code: '1234' })
    expect(result.current.user).toEqual({ id: 4, role: 'citizen', zone_id: 3 })
  })

  it('requestOtp calls the otp/request endpoint without touching the session', async () => {
    api.post.mockResolvedValue({ dev_otp: '1234' })
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

    await act(async () => {
      await result.current.requestOtp('9110001111')
    })

    expect(api.post).toHaveBeenCalledWith('/auth/otp/request', { phone: '9110001111' })
    expect(result.current.user).toBeNull()
  })

  it('logout clears the token and the persisted user', async () => {
    sessionStorage.setItem('rahat_user', JSON.stringify({ id: 1, role: 'citizen', zone_id: 1 }))
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

    act(() => {
      result.current.logout()
    })

    expect(setToken).toHaveBeenCalledWith(null)
    expect(result.current.user).toBeNull()
    expect(sessionStorage.getItem('rahat_user')).toBeNull()
  })

  it('useAuth throws outside of an AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow(/useAuth must be used within/)
  })
})
