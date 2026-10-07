import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { api, clearToken, getToken, setToken, UNAUTHORIZED_EVENT } from './api'

interface AuthState {
  username: string | null
  ready: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(null)
  // With no stored token there is nothing to verify, so we start ready.
  const [ready, setReady] = useState(() => !getToken())

  // A stored token may have expired while the tab was closed; ask the API.
  useEffect(() => {
    let cancelled = false
    if (!getToken()) return
    api.auth
      .me()
      .then((operator) => !cancelled && setUsername(operator.username))
      .catch(() => !cancelled && clearToken())
      .finally(() => !cancelled && setReady(true))
    return () => {
      cancelled = true
    }
  }, [])

  // Any 401 from anywhere in the app drops us back to the login screen.
  useEffect(() => {
    const onUnauthorized = () => setUsername(null)
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [])

  const login = useCallback(async (name: string, password: string) => {
    const { access_token } = await api.auth.login(name, password)
    setToken(access_token)
    const operator = await api.auth.me()
    setUsername(operator.username)
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.auth.logout()
    } catch {
      /* the session may already be gone server-side; clear locally regardless */
    }
    clearToken()
    setUsername(null)
  }, [])

  const value = useMemo(
    () => ({ username, ready, login, logout }),
    [username, ready, login, logout],
  )
  return <AuthContext value={value}>{children}</AuthContext>
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
