import { createContext, useContext, useState, useCallback } from 'react'
import { api, setToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = sessionStorage.getItem('rahat_user')
    return stored ? JSON.parse(stored) : null
  })

  const persistUser = useCallback((u) => {
    setUser(u)
    if (u) {
      sessionStorage.setItem('rahat_user', JSON.stringify(u))
    } else {
      sessionStorage.removeItem('rahat_user')
    }
  }, [])

  const loginWithPassword = useCallback(
    async (email, password, role) => {
      const data = await api.post('/auth/login', { email, password, role })
      setToken(data.access_token)
      persistUser({ id: data.user_id, role: data.role })
      return data
    },
    [persistUser]
  )

  const requestOtp = useCallback(async (phone) => {
    return api.post('/auth/otp/request', { phone })
  }, [])

  const verifyOtp = useCallback(
    async (phone, code) => {
      const data = await api.post('/auth/otp/verify', { phone, code })
      setToken(data.access_token)
      persistUser({ id: data.user_id, role: data.role })
      return data
    },
    [persistUser]
  )

  const logout = useCallback(() => {
    setToken(null)
    persistUser(null)
  }, [persistUser])

  return (
    <AuthContext.Provider value={{ user, loginWithPassword, requestOtp, verifyOtp, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
