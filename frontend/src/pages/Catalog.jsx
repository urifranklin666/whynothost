import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import InstallModal from '../components/InstallModal.jsx'

const CATEGORY_LABELS = {
  all: 'All', files: 'Files', media: 'Media', dev: 'Dev', networking: 'Network',
  security: 'Security', automation: 'Automation', home: 'Home', reading: 'Reading', writing: 'Writing',
}

export default function Catalog() {
  const [data, setData] = useState(null)
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('all')
  const [installing, setInstalling] = useState(null) // app being installed
  const nav = useNavigate()

  useEffect(() => {
    let alive = true
    api.get(`/catalog?q=${encodeURIComponent(q)}&category=${cat}`)
      .then((d) => alive && setData(d))
      .catch(() => {})
    return () => { alive = false }
  }, [q, cat])

  if (!data) {
    return <div className="d-flex justify-content-center py-5"><div className="spinner-border" style={{ color: 'var(--wnh-accent)' }} /></div>
  }

  const featured = data.apps.filter((a) => a.featured)

  return (
    <div>
      <div className="d-flex align-items-center justify-content-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="mb-0" style={{ fontWeight: 800 }}>App Store</h3>
          <div className="wnh-muted">{data.apps.length} apps ready for one-click deploy</div>
        </div>
        <input
          className="form-control wnh-search"
          style={{ maxWidth: 300 }}
          placeholder="Search apps…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      <div className="d-flex gap-2 mb-4 flex-wrap">
        {['all', ...data.categories].map((c) => (
          <button key={c} className={`wnh-chip${cat === c ? ' active' : ''}`} onClick={() => setCat(c)}>
            {CATEGORY_LABELS[c] || c}
          </button>
        ))}
      </div>

      {cat === 'all' && q === '' && featured.length > 0 && (
        <>
          <div className="wnh-muted small mb-2">⭐ Featured</div>
          <div className="row g-3 mb-4">
            {featured.map((a) => <AppTile key={a.id} app={a} onInstall={() => setInstalling(a)} />)}
          </div>
          <div className="wnh-muted small mb-2">All apps</div>
        </>
      )}

      <div className="row g-3">
        {(cat === 'all' && q === '' ? data.apps.filter((a) => !a.featured) : data.apps).map((a) => (
          <AppTile key={a.id} app={a} onInstall={() => setInstalling(a)} />
        ))}
      </div>

      {installing && (
        <InstallModal
          app={installing}
          onClose={() => setInstalling(null)}
          onInstalled={(id) => { setInstalling(null); nav(`/apps/${id}`) }}
        />
      )}
    </div>
  )
}

function AppTile({ app, onInstall }) {
  return (
    <div className="col-12 col-sm-6 col-lg-4 col-xl-3">
      <div className="wnh-card wnh-tile p-3 d-flex flex-column">
        <div className="d-flex align-items-start gap-3 mb-2">
          <div className="wnh-app-icon" style={{ background: `${app.color}22`, borderColor: `${app.color}55` }}>{app.icon}</div>
          <div className="flex-grow-1" style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 700 }}>{app.name}</div>
            <div className="wnh-muted" style={{ fontSize: 12 }}>v{app.version}</div>
          </div>
        </div>
        <div className="wnh-muted flex-grow-0" style={{ fontSize: 13, minHeight: 34 }}>{app.tagline}</div>
        <button className="btn wnh-btn-accent btn-sm mt-3" onClick={onInstall}>Install</button>
      </div>
    </div>
  )
}