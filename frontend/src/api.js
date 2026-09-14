const BASE = '/api'

async function handle(res) {
  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent('wnh:logout'))
    throw new Error('Not authenticated')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = await res.json()
      detail = j.detail || JSON.stringify(j)
    } catch {}
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  get: (path) => fetch(`${BASE}${path}`).then(handle),
  post: (path, body) =>
    fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    }).then(handle),
  del: (path) => fetch(`${BASE}${path}`, { method: 'DELETE' }).then(handle),
}

export function fmtBytes(n) {
  if (!n && n !== 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function fmtUptime(s) {
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  return d > 0 ? `${d}d ${h}h` : h > 0 ? `${h}h ${m}m` : `${m}m`
}