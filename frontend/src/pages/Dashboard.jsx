import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts'
import { api, fmtBytes, fmtUptime } from '../api.js'

export default function Dashboard() {
  const [sys, setSys] = useState(null)
  const [apps, setApps] = useState([])
  const [hist, setHist] = useState([])

  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const [s, a] = await Promise.all([api.get('/system'), api.get('/apps')])
        if (!alive) return
        setSys(s)
        setApps(a)
        setHist((h) => [
          ...h.slice(-29),
          {
            t: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            cpu: s?.stats?.load ? +(s.stats.load['1m'] / (s.stats.load.cores || 1) * 100).toFixed(1) : 0,
            mem: s?.stats?.memory?.percent ?? 0,
          },
        ])
      } catch {}
    }
    tick()
    const iv = setInterval(tick, 3000)
    return () => { alive = false; clearInterval(iv) }
  }, [])

  if (!sys) {
    return <div className="d-flex justify-content-center py-5"><div className="spinner-border" style={{ color: 'var(--wnh-accent)' }} /></div>
  }

  const mem = sys.stats?.memory
  const disk = sys.stats?.disk
  const running = apps.filter((a) => a.status === 'running').length
  const modeBadge = sys.mode === 'live' ? 'green' : 'yellow'

  const gauge = (value, color, label) => (
    <div style={{ position: 'relative', height: 130 }}>
      <ResponsiveContainer>
        <RadialBarChart innerRadius="72%" outerRadius="100%" data={[{ v: value }]} startAngle={220} endAngle={-40}>
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar dataKey="v" cornerRadius={8} fill={color} background={{ fill: 'rgba(255,255,255,0.07)' }} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
        <div style={{ fontSize: 22, fontWeight: 700 }}>{value}%</div>
        <div className="wnh-muted" style={{ fontSize: 11 }}>{label}</div>
      </div>
    </div>
  )

  return (
    <div>
      <div className="d-flex align-items-center justify-content-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="mb-0" style={{ fontWeight: 800 }}>Dashboard</h3>
          <div className="wnh-muted">
            <span className={`wnh-dot ${modeBadge} me-2`} />
            {sys.mode === 'live' ? 'Live mode — real containers' : 'Demo mode — simulated deployments'}
            {sys.live_available === false && sys.mode === 'simulated' && (
              <span className="ms-2" style={{ fontSize: 12 }}>(Docker daemon unreachable)</span>
            )}
          </div>
        </div>
        <Link to="/catalog" className="btn wnh-btn-accent">+ Install an app</Link>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="wnh-card p-3 h-100">
            <div className="wnh-muted small">Apps running</div>
            <div className="wnh-stat">{running}<span className="wnh-muted" style={{ fontSize: 15 }}>/{apps.length}</span></div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="wnh-card p-3 h-100">
            <div className="wnh-muted small">Uptime</div>
            <div className="wnh-stat" style={{ fontSize: '1.35rem', paddingTop: 8 }}>{fmtUptime(sys.stats?.uptime_s || 0)}</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="wnh-card p-3 h-100">
            <div className="wnh-muted small">Memory</div>
            <div className="wnh-stat" style={{ fontSize: '1.35rem', paddingTop: 8 }}>{fmtBytes(mem?.used || 0)} <span className="wnh-muted" style={{ fontSize: 13 }}>of {fmtBytes(mem?.total || 0)}</span></div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="wnh-card p-3 h-100">
            <div className="wnh-muted small">Backups</div>
            <div className="wnh-stat" style={{ fontSize: '1.35rem', paddingTop: 8 }}>{fmtBytes(sys.backup_bytes)}</div>
          </div>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-8">
          <div className="wnh-card p-3 h-100">
            <div className="wnh-muted small mb-2">CPU load &amp; memory — last 90s</div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={hist} margin={{ top: 5, right: 5, left: -22, bottom: 0 }}>
                <defs>
                  <linearGradient id="gCpu" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6c8cff" stopOpacity={0.55} />
                    <stop offset="100%" stopColor="#6c8cff" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gMem" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22d3a5" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#22d3a5" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="t" tick={{ fill: '#8b93b8', fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={40} />
                <YAxis domain={[0, 100]} tick={{ fill: '#8b93b8', fontSize: 10 }} tickLine={false} axisLine={false} unit="%" />
                <Tooltip contentStyle={{ background: '#131a38', border: '1px solid rgba(255,255,255,.1)', borderRadius: 10, color: '#e8ecf8' }} />
                <Area type="monotone" dataKey="cpu" stroke="#6c8cff" fill="url(#gCpu)" strokeWidth={2} name="CPU" />
                <Area type="monotone" dataKey="mem" stroke="#22d3a5" fill="url(#gMem)" strokeWidth={2} name="Memory" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="col-md-4 d-flex gap-3">
          <div className="wnh-card p-3 flex-grow-1">{gauge(mem?.percent ?? 0, '#22d3a5', 'memory')}</div>
          <div className="wnh-card p-3 flex-grow-1">{gauge(disk?.percent ?? 0, '#6c8cff', 'disk')}</div>
        </div>
      </div>

      <div className="row g-3">
        <div className="col-md-7">
          <div className="wnh-card p-3">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <div className="wnh-muted small">Installed apps</div>
              <Link to="/apps" className="text-decoration-none" style={{ fontSize: 13 }}>view all →</Link>
            </div>
            {apps.length === 0 && (
              <div className="wnh-muted py-4 text-center" style={{ fontSize: 14 }}>
                Nothing installed yet — <Link to="/catalog">browse the App Store</Link>
              </div>
            )}
            {apps.slice(0, 6).map((a) => (
              <div key={a.id} className="d-flex align-items-center gap-3 py-2" style={{ borderTop: '1px solid var(--wnh-card-border)' }}>
                <span className="wnh-dot" style={{ background: a.status === 'running' ? 'var(--wnh-accent2)' : 'var(--wnh-danger)' }} />
                <Link to={`/apps/${a.id}`} className="flex-grow-1 text-decoration-none" style={{ color: 'var(--wnh-text)' }}>{a.name}</Link>
                <span className={`badge wnh-badge-${a.status === 'running' ? 'running' : 'stopped'}`}>{a.status}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="col-md-5">
          <div className="wnh-card p-3 h-100">
            <div className="wnh-muted small mb-3">Recent activity</div>
            {sys.activity.length === 0 && <div className="wnh-muted" style={{ fontSize: 14 }}>No activity yet.</div>}
            <div className="wnh-activity">
              {sys.activity.slice(0, 8).map((e) => (
                <div key={e.id} className="wnh-activity-item">
                  <div style={{ fontSize: 14 }}>{e.message}</div>
                  <div className="wnh-muted" style={{ fontSize: 11 }}>{e.ts} · {e.kind}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}