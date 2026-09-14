import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useUser } from '../App.jsx'

const links = [
  { to: '/', label: 'Dashboard', icon: '📊', end: true },
  { to: '/catalog', label: 'App Store', icon: '🛍️' },
  { to: '/apps', label: 'My Apps', icon: '📦' },
  { to: '/system', label: 'System', icon: '⚙️' },
]

export default function Sidebar() {
  const user = useUser()
  const nav = useNavigate()

  const logout = async () => {
    try { await api.post('/auth/logout') } catch {}
    nav('/login')
    window.location.reload()
  }

  return (
    <nav className="wnh-sidebar d-none d-md-flex flex-column" style={{ width: 230, flexShrink: 0 }}>
      <div className="d-flex align-items-center gap-2 px-2 mb-4">
        <span style={{ fontSize: 26 }}>🐳</span>
        <div>
          <div style={{ fontWeight: 800, fontSize: 18, letterSpacing: '-0.02em' }}>WhyNotHost</div>
          <div className="wnh-muted" style={{ fontSize: 11 }}>self-host anything</div>
        </div>
      </div>

      {links.map((l) => (
        <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => `wnh-navlink${isActive ? ' active' : ''}`}>
          <span>{l.icon}</span> {l.label}
        </NavLink>
      ))}

      {user?.role === 'admin' && (
        <NavLink to="/users" className={({ isActive }) => `wnh-navlink${isActive ? ' active' : ''}`}>
          <span>👥</span> Users
        </NavLink>
      )}

      <div className="mt-auto px-2">
        <div className="wnh-muted small mb-2">Signed in as <b style={{ color: 'var(--wnh-text)' }}>{user?.username}</b></div>
        <button className="btn wnh-btn-ghost btn-sm w-100" onClick={logout}>Sign out</button>
      </div>
    </nav>
  )
}