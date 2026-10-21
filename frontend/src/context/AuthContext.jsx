import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api, { tokenStore } from '../lib/api'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!tokenStore.get())

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) { setUser(null); setLoading(false); return null }
    try {
      const { data } = await api.get('/auth/me')
      setUser(data)
      return data
    } catch {
      tokenStore.clear()
      setUser(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const onLogout = () => setUser(null)
    window.addEventListener('bb:logout', onLogout)
    return () => window.removeEventListener('bb:logout', onLogout)
  }, [refresh])

  const login = async (email, password, role) => {
    const { data } = await api.post('/auth/login', { email, password, role })
    tokenStore.set(data.access_token)
    return refresh()
  }

  const register = async (payload) => {
    const { data } = await api.post('/auth/register', payload)
    tokenStore.set(data.access_token)
    return refresh()
  }

  const logout = () => {
    api.post('/auth/logout').catch(() => {})
    tokenStore.clear()
    setUser(null)
  }

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, logout, refresh }}>
      {children}
    </AuthCtx.Provider>
  )
}

export const useAuth = () => useContext(AuthCtx)
