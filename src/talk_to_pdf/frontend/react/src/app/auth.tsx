import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'

import { ApiError, TalkToPdfApi, isApiError } from '@/api/client'
import { API_BASE_URL } from '@/lib/env'
import { clearStoredToken, readStoredToken, writeStoredToken } from '@/lib/storage'
import type { AuthUser, LoginRequest, RegisterRequest } from '@/types/auth'

type AuthStatus = 'loading' | 'authenticated' | 'guest'

interface AuthContextValue {
  status: AuthStatus
  token: string | null
  user: AuthUser | null
  notice: string | null
  login: (payload: LoginRequest) => Promise<AuthUser>
  registerAndLogin: (payload: RegisterRequest) => Promise<AuthUser>
  logout: (notice?: string | null) => void
  clearNotice: () => void
  expireSession: (message?: string) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function createBootstrapApi(onUnauthorized?: (error: ApiError) => void) {
  return new TalkToPdfApi({
    getToken: () => null,
    onUnauthorized,
  })
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [token, setToken] = useState<string | null>(() => readStoredToken())
  const [user, setUser] = useState<AuthUser | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const clearNotice = useCallback(() => {
    setNotice(null)
  }, [])

  const setSession = useCallback((nextToken: string | null, nextUser: AuthUser | null) => {
    if (nextToken) {
      writeStoredToken(nextToken)
    } else {
      clearStoredToken()
    }

    setToken(nextToken)
    setUser(nextUser)
    setStatus(nextUser ? 'authenticated' : 'guest')
  }, [])

  const expireSession = useCallback(
    (message = 'Session expired. Please sign in again.') => {
      setSession(null, null)
      setNotice(message)
    },
    [setSession],
  )

  const bootstrapApi = useMemo(() => createBootstrapApi(), [])

  useEffect(() => {
    const initialize = async () => {
      const storedToken = readStoredToken()
      setToken(storedToken)

      try {
        const me = await bootstrapApi.getMe(storedToken)
        setUser(me)
        setStatus('authenticated')
      } catch (error) {
        if (storedToken && isApiError(error) && error.status === 401) {
          clearStoredToken()
          setNotice('Session expired. Please sign in again.')
        }

        setToken(null)
        setUser(null)
        setStatus('guest')
      }
    }

    void initialize()
  }, [bootstrapApi])

  const login = useCallback(
    async (payload: LoginRequest) => {
      const api = createBootstrapApi()
      const response = await api.login(payload)
      const me = await api.getMe(response.access_token)
      setNotice(null)
      setSession(response.access_token, me)
      return me
    },
    [setSession],
  )

  const registerAndLogin = useCallback(
    async (payload: RegisterRequest) => {
      const api = createBootstrapApi()
      await api.register(payload)
      return login({
        email: payload.email,
        password: payload.password,
      })
    },
    [login],
  )

  const logout = useCallback(
    (nextNotice?: string | null) => {
      setSession(null, null)
      setNotice(nextNotice ?? null)
    },
    [setSession],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      token,
      user,
      notice,
      login,
      registerAndLogin,
      logout,
      clearNotice,
      expireSession,
    }),
    [clearNotice, expireSession, login, logout, notice, registerAndLogin, status, token, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error(`useAuth must be used inside AuthProvider for ${API_BASE_URL}`)
  }

  return context
}

export function useApiClient() {
  const { expireSession, token } = useAuth()

  return useMemo(
    () =>
      new TalkToPdfApi({
        getToken: () => token,
        onUnauthorized: () => {
          expireSession()
        },
      }),
    [expireSession, token],
  )
}
