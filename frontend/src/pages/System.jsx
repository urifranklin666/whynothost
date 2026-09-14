import React, { useEffect, useState } from 'react'
import { api, fmtBytes, fmtUptime } from '../api.js'

export default function System() {
  const [sys, setSys] = useState(null)
  const [proxyText, setProxyText] = useState(null)
  const [edge, setEdge] = useState(null)
  const [edgeText, setEdgeText] = useState(null)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [edgeBusy, setEdgeBusy] = useState(false)

  const load = () => {
    api.get('/system').then(setSys).catch(() => {})
    api.get('/system/edge').then(setEdge).catch(() => {})
  }

  useEffect(() => {
    load()
    const iv = setInterval(load, 5000)
    return () => clearInterval(iv)
  }, [])

  const setMode = async (mode) => {
    setErr(''); setMsg('')
    try {
      await api.post('/system/mode', { mode })
      setMsg(`Engine set to ${mode}.`)
      load()
    } catch (e) { setErr(e.message) }
  }

  const loadProxy = async () => {
    try { setProxyText((await api.get('/system/proxy')).caddyfile) } catch (e) { setErr(e.message) }
  }

  const writeProxy = async () => {
    setErr(''); setMsg('')
    try {
      const r = await api.post('/system/proxy/write')
      setMsg(`Caddyfile written to ${r.path}. Reload Caddy to apply.`)
    } catch (e) { setErr(e.message) }
  }

  const edgeAct = async (action, label) => {
    setErr(''); setMsg(''); setEdgeBusy(true)
    try {
      const r = await api.post(`/system/edge/${action}`)
      setMsg(label + (r.running === false && action === 'disable' ? ' — edge stopped.' : ' — check status below.'))
      setTimeout(load, 800)
    } catch (e) { setErr(e.message) } finally { setEdgeBusy(false) }
  }

  if (!sys) {
    return <div className="d-flex justify-content-center py-5"><div className="spinner-border" style={{ color: 'var(--wnh-accent)' }} /></div>
  }

  return (
    <div style={{ maxWidth: 900 }}>
      <h3 className="mb-1" style={{ fontWeight: 800 }}>System</h3>
      <div className="wnh-muted mb-4">Deploy engine, reverse proxy, and host info.</div>

      {msg && <div className="alert alert-success py-2">{msg}</div>}
      {err && <div className="alert alert-danger py-2">{err}</div>}

      <div className="wnh-card p-3 mb-3">
        <div className="wnh-muted small mb-3">Deployment engine</div>
        <div className="d-flex align-items-center gap-2 mb-3">
          <span className={`wnh-dot ${sys.mode === 'live' ? 'green' : 'yellow'}`} />
          <b>{sys.mode === 'live' ? 'Live (Docker Compose)' : 'Simulated (demo mode)'}</b>
          <span className="wnh-muted" style={{ fontSize: 12 }}>
            · docker CLI: {sys.docker_cli ? 'present' : 'missing'} · daemon: {sys.live_available ? 'reachable' : 'unreachable'}
          </span>
        </div>
        <div className="d-flex gap-2 flex-wrap">
          <button className={`btn btn-sm ${sys.override === 'live' ? 'wnh-btn-accent' : 'wnh-btn-ghost'}`} onClick={() => setMode('live')}>Force live</button>
          <button className={`btn btn-sm ${sys.override === 'simulated' ? 'wnh-btn-accent' : 'wnh-btn-ghost'}`} onClick={() => setMode('simulated')}>Force demo</button>
          <button className={`btn btn-sm ${sys.override === null ? 'wnh-btn-accent' : 'wnh-btn-ghost'}`} onClick={() => setMode('auto')}>Auto-detect</button>
        </div>
      </div>

      <div className="wnh-card p-3 mb-3">
        <div className="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-2">
          <div className="wnh-muted small">HTTPS edge proxy (Let's Encrypt)</div>
          {edge && (
            <span className={`badge ${edge.running ? 'wnh-badge-running' : 'wnh-badge-stopped'}`}>
              {edge.running ? 'running' : 'not running'}
            </span>
          )}
        </div>
        <p className="wnh-muted" style={{ fontSize: 13 }}>
          One managed Caddy stack on ports <code className="wnh-code">80</code>/<code className="wnh-code">443</code> fronts the
          dashboard and every running app. Public domains get real <b>Let's Encrypt</b> certificates automatically;
          reserved local domains (<code className="wnh-code">*.home.arpa</code>, <code className="wnh-code">*.local</code>, …) use
          self-signed <code className="wnh-code">tls internal</code>. Certificates persist in <code className="wnh-code">{sys.proxy.caddyfile.replace(/Caddyfile$/, 'edge/')}caddy/data</code>.
        </p>
        <div className="d-flex gap-2 flex-wrap mb-2">
          {edge?.running
            ? <>
                <button className="btn wnh-btn-ghost btn-sm" disabled={edgeBusy} onClick={() => edgeAct('reload', 'Edge config reloaded (zero-downtime).')}>↻ Reload config</button>
                <button className="btn wnh-btn-ghost btn-sm" disabled={edgeBusy} style={{ color: 'var(--wnh-danger)' }} onClick={() => edgeAct('disable', 'Edge proxy disabled.')}>⏹ Disable</button>
              </>
            : <button className="btn wnh-btn-accent btn-sm" disabled={edgeBusy || sys.mode !== 'live'} onClick={() => edgeAct('enable', 'Edge proxy starting — certificates will be issued on first request.')}>
                🔒 Enable HTTPS
              </button>}
          <button className="btn wnh-btn-ghost btn-sm" onClick={() => setEdgeText(edge?.caddyfile ?? null)}>Preview Caddyfile</button>
        </div>
        {edge && (
          <div className="wnh-muted" style={{ fontSize: 12 }}>
            Ports 80/443: {edge.ports_80_443_free?.['80'] && edge.ports_80_443_free?.['443']
              ? 'free ✔' : 'in use by another service ✖'} · hostname: <code className="wnh-code">{edge.hostname || 'unknown'}</code>
          </div>
        )}
        {edge && edge.apps?.length > 0 && (
          <div className="mt-2">
            {edge.apps.map((a) => (
              <div key={a.id} className="d-flex align-items-center gap-2 py-1" style={{ fontSize: 13, borderTop: '1px solid var(--wnh-card-border)' }}>
                <span className={`wnh-dot ${a.https ? 'green' : 'yellow'}`} />
                <code className="wnh-code">{a.domain}</code>
                <span className="wnh-muted ms-auto" style={{ fontSize: 11 }}>{a.https ? "Let's Encrypt (public)" : 'self-signed (local)'}</span>
              </div>
            ))}
          </div>
        )}
        {edgeText && <pre className="wnh-log mt-2" style={{ maxHeight: 260 }}>{edgeText}</pre>}
      </div>

      <div className="wnh-card p-3 mb-3">
        <div className="wnh-muted small mb-3">Reverse proxy (Caddy)</div>
        <p className="wnh-muted" style={{ fontSize: 13 }}>
          WhyNotHost generates a Caddyfile entry per running app: <code className="wnh-code">&lt;app&gt;.{sys.proxy.domain_suffix}</code> → app port.
          Write it out and point Caddy (or any web server) at it.
        </p>
        <div className="d-flex gap-2 mb-3">
          <button className="btn wnh-btn-ghost btn-sm" onClick={loadProxy}>Preview</button>
          <button className="btn wnh-btn-accent btn-sm" onClick={writeProxy}>Write Caddyfile</button>
        </div>
        {proxyText && <pre className="wnh-log" style={{ maxHeight: 220 }}>{proxyText}</pre>}
      </div>

      <div className="wnh-card p-3">
        <div className="wnh-muted small mb-3">Host</div>
        <div className="row" style={{ fontSize: 14 }}>
          <div className="col-6 py-1"><span className="wnh-muted">Uptime</span> <span className="float-end">{fmtUptime(sys.stats?.uptime_s || 0)}</span></div>
          <div className="col-6 py-1"><span className="wnh-muted">CPU cores</span> <span className="float-end">{sys.stats?.load?.cores ?? '—'}</span></div>
          <div className="col-6 py-1"><span className="wnh-muted">Load (1m / 5m / 15m)</span> <span className="float-end">{sys.stats?.load ? `${sys.stats.load['1m']} / ${sys.stats.load['5m']} / ${sys.stats.load['15m']}` : '—'}</span></div>
          <div className="col-6 py-1"><span className="wnh-muted">Memory</span> <span className="float-end">{fmtBytes(sys.stats?.memory?.used)} / {fmtBytes(sys.stats?.memory?.total)}</span></div>
          <div className="col-6 py-1"><span className="wnh-muted">Disk</span> <span className="float-end">{fmtBytes(sys.stats?.disk?.used)} / {fmtBytes(sys.stats?.disk?.total)} ({sys.stats?.disk?.percent}%)</span></div>
          <div className="col-6 py-1"><span className="wnh-muted">Backups on disk</span> <span className="float-end">{fmtBytes(sys.backup_bytes)}</span></div>
        </div>
      </div>
    </div>
  )
}