import { useState, type FormEvent } from 'react'

import { Alert, Button, Card } from '../components/ui'
import { useAuth } from '../lib/auth'

export default function Login() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(username, password)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Sign-in failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-full place-items-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-leaf-600 text-lg font-bold text-white">
            MT
          </span>
          <div>
            <h1 className="text-lg font-semibold text-bark-900">Madre Tierra</h1>
            <p className="text-sm text-bark-700">Inventory system</p>
          </div>
        </div>

        <Card className="p-6">
          {error && <Alert onDismiss={() => setError('')}>{error}</Alert>}
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="label" htmlFor="username">
                Operator
              </label>
              <input
                id="username"
                className="field"
                autoComplete="username"
                autoFocus
                required
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </div>
            <div>
              <label className="label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                className="field"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </Card>

        <p className="mt-4 text-center text-xs text-bark-700">
          Credentials are set with{' '}
          <code className="rounded bg-bark-100 px-1 py-0.5">python -m app.core.setup_auth</code>
        </p>
      </div>
    </div>
  )
}
