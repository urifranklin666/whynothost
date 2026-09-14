import React, { useEffect, useState } from 'react'
import { useUser } from '../App.jsx'
import { api } from '../api.js'

export default function Users() {
  const user = useUser()
  const [users, setUsers] = useState(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('user')
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  const load = () => api.get('/auth/users').then(setUsers).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [])

  if (user.role !== 'admin') {
    return <div className="wnh-card p-4 wnh-muted">Admin access required.</div>
  }

  const addUser = async (e) => {
    e.preventDefault()
    setErr(''); setMsg('')
    try {
      await api.post('/auth/users', { username, password, role })
      setMsg(`User ${username} created.`)
      setUsername(''); setPassword('')
      load()
    } catch (e2) { setErr(e2.message) }
  }

  const del = async (id, name) => {
    if (!window.confirm(`Delete user ${name}?`)) return
    try { await api.del(`/auth/users/${id}`); load() } catch (e) { setErr(e.message) }
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <h3 className="mb-1" style={{ fontWeight: 800 }}>Users</h3>
      <div className="wnh-muted mb-4">Accounts that can access this dashboard.</div>

      {msg && <div className="alert alert-success py-2">{msg}</div>}
      {err && <div className="alert alert-danger py-2">{err}</div>}

      <div className="wnh-card p-3 mb-3">
        <div className="wnh-muted small mb-3">Create user</div>
        <form className="row g-2 align-items-end" onSubmit={addUser}>
          <div className="col-md-4">
            <label className="form-label">Username</label>
            <input className="form-control" value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
          <div className="col-md-4">
            <label className="form-label">Password (≥ 8 chars)</label>
            <input className="form-control" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
          </div>
          <div className="col-md-2">
            <label className="form-label">Role</label>
            <select className="form-select" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
          </div>
          <div className="col-md-2">
            <button className="btn wnh-btn-accent w-100">Create</button>
          </div>
        </form>
      </div>

      <div className="wnh-card p-3">
        <div className="wnh-muted small mb-3">Existing users</div>
        {(users || []).map((u) => (
          <div key={u.id} className="d-flex align-items-center gap-3 py-2" style={{ borderBottom: '1px solid var(--wnh-card-border)' }}>
            <div className="wnh-app-icon" style={{ width: 36, height: 36, fontSize: 14 }}>{u.username.slice(0, 2).toUpperCase()}</div>
            <div className="flex-grow-1">
              <b>{u.username}</b>
              {u.id === user.id && <span className="wnh-muted ms-2" style={{ fontSize: 12 }}>(you)</span>}
            </div>
            <span className={`badge ${u.role === 'admin' ? 'wnh-badge-running' : 'wnh-badge-installing'}`}>{u.role}</span>
            {u.id !== user.id && (
              <button className="btn wnh-btn-ghost btn-sm" style={{ color: 'var(--wnh-danger)' }} onClick={() => del(u.id, u.username)}>✖</button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}