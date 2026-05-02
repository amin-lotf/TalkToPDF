import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'

import { useAuth } from '@/app/auth'
import { AuthShell } from '@/components/layout/AuthShell'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

export function RegisterPage() {
  const navigate = useNavigate()
  const { registerAndLogin } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  return (
    <AuthShell
      title="Register"
      subtitle="Use the backend's built-in `/auth/register` endpoint and sign in immediately after creation."
      footer={
        <span>
          Already have an account?{' '}
          <Link className="font-medium text-sky-300 hover:text-sky-200" to="/login">
            Back to login
          </Link>
        </span>
      }
    >
      <form
        className="space-y-4"
        onSubmit={async (event) => {
          event.preventDefault()
          setError(null)

          if (password !== confirmPassword) {
            setError('Passwords do not match.')
            return
          }

          setSubmitting(true)
          try {
            await registerAndLogin({
              email,
              name,
              password,
            })
            navigate('/dashboard')
          } catch (registrationError) {
            setError(registrationError instanceof Error ? registrationError.message : 'Failed to create account.')
          } finally {
            setSubmitting(false)
          }
        }}
      >
        {error ? <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</div> : null}

        <label className="block space-y-2 text-sm">
          <span className="text-slate-300">Name</span>
          <Input value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={50} required />
        </label>

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
            autoComplete="new-password"
            minLength={8}
            maxLength={128}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        <label className="block space-y-2 text-sm">
          <span className="text-slate-300">Confirm password</span>
          <Input
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
          />
        </label>

        <Button type="submit" className="w-full" loading={submitting}>
          Create account
        </Button>
      </form>
    </AuthShell>
  )
}
