import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function InstallModal({ app, onClose, onInstalled }) {
  const [config, setConfig] = useState({})
  const [stage, setStage] = useState('config') // config | deploying | done | error
  const [logs, setLogs] = useState([])
  const [err, setErr] = useState('')
  const [preview, setPreview] = useState(null)
  const [showPreview, setShowPreview] = useState(false)

  useEffect(() => {
    const def = {}
    for (const p of app.config || []) def[p.key] = p.default ?? ''
    setConfig(def)
  }, [app])

  useEffect(() => {
    if (stage !== 'config') return
    let alive = true
    const t = setTimeout(() => {
      api.post(`/compose-preview/${app.id}`, config)
        .then((d) => alive && (setPreview(d.compose), setErr('')))
        .catch((e) => alive && setErr(e.message))
    }, 300)
    return () => { alive = false; clearTimeout(t) }
  }, [config, stage, app.id])

  // live SSE progress while deploying
  useEffect(() => {
    if (stage !== 'deploying') return
    const es = new EventSource('/api/events')
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        if (data.type === 'job' && data.app_id === app.id) {
          setLogs((l) => [...l, data.message].slice(-30))
          if (data.stage === 'done') {
            es.close()
            setStage('done')
            setTimeout(() => onInstalled(app.id), 600)
          }
          if (data.stage === 'error') {
            es.close()
            setErr(data.message)
            setStage('error')
          }
        }
      } catch {}
    }
    es.onerror = () => { /* keep-open is fine */ }
    return () => es.close()
  }, [stage, app.id, onInstalled])

  const install = async () => {
    setErr('')
    try {
      const res = await api.post(`/apps/${app.id}/install`, { config })
      if (!res.ok) throw new Error(res.error || 'install failed')
      setLogs(['Starting deployment…'])
      setStage('deploying')
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <div className="wnh-modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget && stage === 'config') onClose() }}>
      <div className="wnh-card p-4" style={{ width: 560, maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="d-flex align-items-center gap-3 mb-1">
          <div className="wnh-app-icon" style={{ background: `${app.color}22`, borderColor: `${app.color}55` }}>{app.icon}</div>
          <div className="flex-grow-1">
            <h5 className="mb-0" style={{ fontWeight: 700 }}>Install {app.name}</h5>
            <div className="wnh-muted" style={{ fontSize: 13 }}>{app.tagline}</div>
          </div>
          {stage === 'config' && <button className="btn-close btn-close-white" onClick={onClose} />}
        </div>

        {stage === 'config' && (
          <>
            <p className="wnh-muted mt-2" style={{ fontSize: 13 }}>{app.description}</p>
            {(app.config || []).map((p) => (
              <div className="mb-3" key={p.key}>
                <label className="form-label">
                  {p.label}{p.required && <span style={{ color: 'var(--wnh-danger)' }}> *</span>}
                </label>
                {p.type === 'bool' ? (
                  <select
                    className="form-select"
                    value={config[p.key] ?? 'false'}
                    onChange={(e) => setConfig({ ...config, [p.key]: e.target.value })}
                  >
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </select>
                ) : (
                  <input
                    className="form-control"
                    type={p.type === 'secret' ? 'password' : 'text'}
                    placeholder={p.default || ''}
                    value={config[p.key] ?? ''}
                    onChange={(e) => setConfig({ ...config, [p.key]: e.target.value })}
                  />
                )}
              </div>
            ))}

            {preview && (
              <>
                <button className="btn wnh-btn-ghost btn-sm mb-2" onClick={() => setShowPreview(!showPreview)}>
                  {showPreview ? 'Hide' : 'Preview'} compose file
                </button>
                {showPreview && <pre className="wnh-log" style={{ maxHeight: 200 }}>{preview}</pre>}
              </>
            )}

            {err && <div className="alert alert-danger py-2 mt-2" style={{ fontSize: '.85rem' }}>{err}</div>}

            <div className="d-flex gap-2 mt-3">
              <button className="btn wnh-btn-ghost flex-fill" onClick={onClose}>Cancel</button>
              <button className="btn wnh-btn-accent flex-fill" onClick={install}>🚀 Deploy now</button>
            </div>
          </>
        )}

        {(stage === 'deploying' || stage === 'done' || stage === 'error') && (
          <>
            <div className="mt-3 mb-2 d-flex align-items-center gap-2">
              {stage === 'deploying' && <div className="spinner-border spinner-border-sm" style={{ color: 'var(--wnh-accent)' }} />}
              {stage === 'done' && <span style={{ color: 'var(--wnh-accent2)' }}>✔</span>}
              {stage === 'error' && <span style={{ color: 'var(--wnh-danger)' }}>✖</span>}
              <b>
                {stage === 'deploying' && 'Deploying…'}
                {stage === 'done' && 'Deployed!'}
                {stage === 'error' && 'Deployment failed'}
              </b>
            </div>
            {err && stage === 'error' && <div className="alert alert-danger py-2" style={{ fontSize: '.85rem' }}>{err}</div>}
            <div className="wnh-progress progress mb-2">
              <div className="progress-bar progress-bar-striped progress-bar-animated" style={{ width: stage === 'done' ? '100%' : '60%' }} />
            </div>
            <pre className="wnh-log">{logs.join('\n')}</pre>
            {stage === 'done' && <div className="wnh-muted text-center mt-2" style={{ fontSize: 13 }}>Opening app page…</div>}
          </>
        )}
      </div>
    </div>
  )
}