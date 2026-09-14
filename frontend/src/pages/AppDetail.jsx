import React, { useEffect, useState, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { api, fmtBytes } from '../api.js'

export default function AppDetail() {
  const { appId } = useParams()
  const nav = useNavigate()
  const [app, setApp] = useState(null)
  const [manifest, setManifest] = useState(null)
  const [logs, setLogs] = useState('')
  const [backups, setBackups] = useState([])
  const [err, setErr] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const logRef = useRef(null)

  const load = () => {
    api.get(`/apps/${appId}`).then(setApp).catch((e) => setErr(e.message))
    api.get(`/catalog/${appId}`).then(setManifest).catch(() => {})
    api.get(`/apps/${appId}/logs?tail=150`).then((d) => setLogs(d.logs)).catch(() => {})
    api.get(`/apps/${appId}/backups`).then(setBackups).catch(() => {})
  }

  useEffect(() => {
    load()
    const iv = setInterval(() => {
      api.get(`/apps/${appId}`).then(setApp).catch(() => {})
      api.get(`/apps/${appId}/logs?tail=150`).then((d) => setLogs(d.logs)).catch(() => {})
    }, 4000)
    return () => clearInterval(iv)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logs])

  const act = async (action) => {
    setErr('')
    try { await api.post(`/apps/${appId}/${action}`); setTimeout(load, 600) } catch (e) { setErr(e.message) }
  }

  const doBackup = async () => {
    setErr('')
    try { await api.post(`/apps/${appId}/backup/create`); setTimeout(load, 300) } catch (e) { setErr(e.message) }
  }

  const restore = async (f) => {
    setErr('')
    try { await api.post(`/apps/${appId}/backups/${encodeURIComponent(f)}/restore`); setErr('') } catch (e) { setErr(e.message) }
  }

  const delBackup = async (f) => {
    try { await api.del(`/apps/${appId}/backups/${encodeURIComponent(f)}`); load() } catch (e) { setErr(e.message) }
  }

  const uninstall = async () => {
    try {
      await api.post(`/apps/${appId}/uninstall`)
      nav('/apps')
    } catch (e) { setErr(e.message) }
  }

  if (!app && !err) {
    return <div className="d-flex justify-content-center py-5"><div className="spinner-border" style={{ color: 'var(--wnh-accent)' }} /></div>
  }

  const running = app?.status === 'running'
  const domain = app?.config?.domain

  return (
    <div>
      <button className="btn wnh-btn-ghost btn-sm mb-3" onClick={() => nav(-1)}>← Back</button>
      {err && <div className="alert alert-danger py-2">{err}</div>}
      {!app && <div className="wnh-card p-4 wnh-muted">App not installed.</div>}

      {app && (
        <>
          <div className="d-flex align-items-center gap-3 mb-4 flex-wrap">
            <div className="wnh-app-icon" style={{ width: 56, height: 56, fontSize: 28, background: `${manifest?.color || '#6c8cff'}22`, borderColor: `${manifest?.color || '#6c8cff'}55` }}>
              {manifest?.icon || '📦'}
            </div>
            <div className="flex-grow-1">
              <h3 className="mb-0" style={{ fontWeight: 800 }}>{app.name}</h3>
              <div className="wnh-muted">
                <span className={`wnh-dot ${running ? 'green' : 'red'} me-2`} />
                {running ? 'Running' : 'Stopped'} · v{app.catalog_version}
              </div>
            </div>
            <div className="d-flex gap-2 flex-wrap">
              {!running
                ? <button className="btn wnh-btn-accent" onClick={() => act('start')}>▶ Start</button>
                : <button className="btn wnh-btn-ghost" onClick={() => act('stop')}>⏸ Stop</button>}
              <button className="btn wnh-btn-ghost" onClick={() => act('restart')}>↻ Restart</button>
              <button className="btn wnh-btn-ghost" onClick={() => act('update')}>⬆ Update</button>
              {!confirmDelete
                ? <button className="btn wnh-btn-ghost" style={{ color: 'var(--wnh-danger)' }} onClick={() => setConfirmDelete(true)}>🗑 Uninstall</button>
                : <>
                    <button className="btn btn-danger" onClick={uninstall}>Really uninstall?</button>
                    <button className="btn wnh-btn-ghost" onClick={() => setConfirmDelete(false)}>Cancel</button>
                  </>}
            </div>
          </div>

          <div className="row g-3">
            <div className="col-lg-7">
              <div className="wnh-card p-3 mb-3">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <div className="wnh-muted small">Container logs</div>
                  <span className="wnh-muted" style={{ fontSize: 11 }}>auto-refresh 4s</span>
                </div>
                <pre className="wnh-log" ref={logRef}>{logs || 'No logs yet.'}</pre>
              </div>

              <div className="wnh-card p-3">
                <div className="wnh-muted small mb-3">Backups</div>
                <button className="btn wnh-btn-accent btn-sm mb-3" onClick={doBackup}>+ Create backup</button>
                {backups.length === 0 && <div className="wnh-muted" style={{ fontSize: 13 }}>No backups yet.</div>}
                {backups.map((b) => (
                  <div key={b.file} className="d-flex align-items-center gap-2 py-2" style={{ borderTop: '1px solid var(--wnh-card-border)' }}>
                    <span style={{ fontSize: 16 }}>💾</span>
                    <div className="flex-grow-1" style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13 }}>{b.file}</div>
                      <div className="wnh-muted" style={{ fontSize: 11 }}>{fmtBytes(b.size)} · {b.created}</div>
                    </div>
                    <button className="btn wnh-btn-ghost btn-sm" onClick={() => restore(b.file)}>Restore</button>
                    <button className="btn wnh-btn-ghost btn-sm" style={{ color: 'var(--wnh-danger)' }} onClick={() => delBackup(b.file)}>✖</button>
                  </div>
                ))}
              </div>
            </div>

            <div className="col-lg-5">
              <div className="wnh-card p-3 mb-3">
                <div className="wnh-muted small mb-3">Access</div>
                {domain && (
                  <div className="mb-2">
                    <div className="wnh-muted" style={{ fontSize: 12 }}>Local domain</div>
                    <code className="wnh-code">https://{domain}</code>
                    <div className="wnh-muted mt-1" style={{ fontSize: 11 }}>
                      Point a DNS record (or /etc/hosts entry) at this host, then run <b>System → Reverse proxy</b> to activate.
                    </div>
                  </div>
                )}
                {app.config?.port && (
                  <div>
                    <div className="wnh-muted" style={{ fontSize: 12 }}>Direct port</div>
                    <code className="wnh-code">http://127.0.0.1:{app.config.port}</code>
                  </div>
                )}
              </div>

              <div className="wnh-card p-3 mb-3">
                <div className="wnh-muted small mb-3">Configuration</div>
                {Object.entries(app.config).map(([k, v]) => (
                  <div key={k} className="d-flex justify-content-between py-1" style={{ fontSize: 13, borderBottom: '1px solid var(--wnh-card-border)' }}>
                    <span className="wnh-muted">{k}</span>
                    <span style={{ fontFamily: 'ui-monospace, monospace' }}>{String(k === 'admin_password' || k.endsWith('password') ? '••••••' : v)}</span>
                  </div>
                ))}
              </div>

              <div className="wnh-card p-3">
                <div className="wnh-muted small mb-3">Services</div>
                {(app.runtime?.services || []).length === 0 && <div className="wnh-muted" style={{ fontSize: 13 }}>No running services.</div>}
                {(app.runtime?.services || []).map((s, i) => (
                  <div key={i} className="d-flex justify-content-between align-items-center py-1" style={{ fontSize: 13 }}>
                    <span>{s.Name || s.Service || 'service'}</span>
                    <span className={`badge wnh-badge-${s.State === 'running' ? 'running' : 'stopped'}`}>{s.State}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}