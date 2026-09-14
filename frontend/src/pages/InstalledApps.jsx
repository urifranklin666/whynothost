import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

export default function InstalledApps() {
  const [apps, setApps] = useState(null)

  useEffect(() => {
    let alive = true
    const tick = () => api.get('/apps').then((a) => alive && setApps(a)).catch(() => {})
    tick()
    const iv = setInterval(tick, 4000)
    return () => { alive = false; clearInterval(iv) }
  }, [])

  if (!apps) {
    return <div className="d-flex justify-content-center py-5"><div className="spinner-border" style={{ color: 'var(--wnh-accent)' }} /></div>
  }

  return (
    <div>
      <div className="d-flex align-items-center justify-content-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="mb-0" style={{ fontWeight: 800 }}>My Apps</h3>
          <div className="wnh-muted">{apps.length} installed</div>
        </div>
        <Link to="/catalog" className="btn wnh-btn-accent">+ Install an app</Link>
      </div>

      {apps.length === 0 && (
        <div className="wnh-card p-5 text-center wnh-muted">
          <div style={{ fontSize: 40 }}>📦</div>
          No apps installed yet. Head to the <Link to="/catalog">App Store</Link>.
        </div>
      )}

      <div className="row g-3">
        {apps.map((a) => (
          <div className="col-12 col-sm-6 col-lg-4" key={a.id}>
            <Link to={`/apps/${a.id}`} className="text-decoration-none">
              <div className="wnh-card wnh-tile p-3">
                <div className="d-flex align-items-center gap-3">
                  <div className="wnh-app-icon">{a.id.slice(0, 2).toUpperCase()}</div>
                  <div className="flex-grow-1" style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 700, color: 'var(--wnh-text)' }}>{a.name}</div>
                    <div className="wnh-muted" style={{ fontSize: 12 }}>v{a.catalog_version} · installed {a.installed_at?.slice(0, 10)}</div>
                  </div>
                  <span className={`badge wnh-badge-${a.status === 'running' ? 'running' : a.status === 'stopped' ? 'stopped' : 'installing'}`}>
                    {a.status}
                  </span>
                </div>
              </div>
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}