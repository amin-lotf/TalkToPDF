import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'

import { useAuth } from '@/app/auth'
import { AuthShell } from '@/components/layout/AuthShell'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

export function LoginPage() {
  const navigate = useNavigate()
  const { clearNotice, login, notice } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  return (
    <AuthShell
      title="Login"
      subtitle="Sign in with the existing JWT flow exposed by the backend."
      footer={
        <span>
          Need an account?{' '}
          <Link className="font-medium text-sky-300 hover:text-sky-200" to="/register">
            Create one
          </Link>
        </span>
      }
    >
      <form
        className="space-y-4"
        onSubmit={async (event) => {
          event.preventDefault()
          setSubmitting(true)
          setError(null)
          clearNotice()

          try {
            await login({
              email,
              password,
            })
            navigate('/dashboard')
          } catch (loginError) {
            setError(loginError instanceof Error ? loginError.message : 'Failed to sign in.')
          } finally {
            setSubmitting(false)
          }
        }}
      >
        {notice ? <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">{notice}</div> : null}
        {error ? <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</div> : null}

        <label className="block space-y-2 text-sm">
          <span className="text-slate-300">Email</span>
          <Input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>

        <label className="block space-y-2 text-sm">
          <span className="text-slate-300">Password</span>
          <Input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        <Button type="submit" className="w-full" loading={submitting}>
          Sign in
        </Button>
      </form>
    </AuthShell>
  )
}
