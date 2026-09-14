import React, { useState } from 'react'
import { api } from '../api.js'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const u = await api.post('/auth/login', { username, password })
      onLogin(u)
    } catch (e2) {
      setErr(e2.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="d-flex align-items-center justify-content-center" style={{ minHeight: '100vh' }}>
      <div className="wnh-card p-4 p-md-5" style={{ width: 400 }}>
        <div className="text-center mb-4">
          <div style={{ fontSize: 44 }}>🐳</div>
          <h3 style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>WhyNotHost</h3>
          <div className="wnh-muted">Self-host anything, in one click</div>
        </div>
        {err && <div className="alert alert-danger py-2" style={{ fontSize: '.9rem' }}>{err}</div>}
        <form onSubmit={submit}>
          <div className="mb-3">
            <label className="form-label">Username</label>
            <input className="form-control" autoFocus value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="mb-4">
            <label className="form-label">Password</label>
            <input className="form-control" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="btn wnh-btn-accent w-100" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <div className="wnh-muted text-center mt-3" style={{ fontSize: 12 }}>
          First run: <code className="wnh-code">admin</code> / <code className="wnh-code">whynothost</code>
        </div>
      </div>
    </div>
  )
}