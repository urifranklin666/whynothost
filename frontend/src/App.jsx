import React, { useEffect, useState, createContext, useContext } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { api } from './api.js'
import Sidebar from './components/Sidebar.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Catalog from './pages/Catalog.jsx'
import InstalledApps from './pages/InstalledApps.jsx'
import AppDetail from './pages/AppDetail.jsx'
import System from './pages/System.jsx'
import Users from './pages/Users.jsx'

const UserCtx = createContext(null)
export const useUser = () => useContext(UserCtx)

export default function App() {
  const [user, setUser] = useState(undefined) // undefined = loading, null = logged out
  const loc = useLocation()

  useEffect(() => {
    const onLogout = () => setUser(null)
    window.addEventListener('wnh:logout', onLogout)
    return () => window.removeEventListener('wnh:logout', onLogout)
  }, [])

  useEffect(() => {
    let alive = true
    api.get('/auth/me')
      .then((u) => alive && setUser(u))
      .catch(() => alive && setUser(null))
    return () => { alive = false }
  }, [])

  if (user === undefined) {
    return (
      <div className="d-flex vh-100 align-items-center justify-content-center">
        <div className="spinner-border" style={{ color: 'var(--wnh-accent)' }} role="status" />
      </div>
    )
  }

  if (!user || loc.pathname === '/login') {
    return (
      <Routes>
        <Route path="/login" element={<Login onLogin={setUser} />} />
        <Route path="*" element={<Navigate to={user ? '/' : '/login'} replace />} />
      </Routes>
    )
  }

  return (
    <UserCtx.Provider value={user}>
      <div className="d-flex">
        <Sidebar />
        <div className="flex-grow-1 p-4" style={{ minWidth: 0 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/catalog" element={<Catalog />} />
            <Route path="/apps" element={<InstalledApps />} />
            <Route path="/apps/:appId" element={<AppDetail />} />
            <Route path="/system" element={<System />} />
            <Route path="/users" element={<Users />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </UserCtx.Provider>
  )
}