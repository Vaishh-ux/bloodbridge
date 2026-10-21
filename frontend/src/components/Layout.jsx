import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { HeartPulse, LayoutDashboard, LogOut, Menu, ShieldCheck, Siren, X, Heart, Droplet } from 'lucide-react'
import Logo from './Logo'
import NotificationBell from './NotificationBell'
import { useAuth } from '../context/AuthContext'
import { DASHBOARD_PATH } from '../lib/blood'

const NAV = [
  { to: '/requests', label: 'Blood Requests' },
  { to: '/find-donors', label: 'Find Donors' },
  { to: '/blood-banks', label: 'Find Blood Banks' },
  { to: '/map', label: 'Live Map' },
  { to: '/donate', label: 'Donate Blood', icon: Heart },
]

export const DISCLAIMER =
  'Blood Bridge is a donor-request coordination platform. Final donor eligibility, compatibility verification, testing, and transfusion decisions must be confirmed by qualified healthcare professionals.'

export default function Layout() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const nav = useNavigate()
  const loc = useLocation()
  useEffect(() => setOpen(false), [loc.pathname])

  const linkCls = ({ isActive }) =>
    `px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition ${isActive ? 'text-blood-600 bg-blood-50' : 'text-slate-600 hover:text-navy-900'}`

  return (
    <div className="min-h-screen flex flex-col">
      <div className="bg-navy-950 text-white text-[11px] sm:text-xs py-1.5 px-4 text-center">
        <ShieldCheck className="inline w-3.5 h-3.5 text-amber-400 mr-1 -mt-0.5" />
        <strong>Medical Safety Notice:</strong> {DISCLAIMER}
      </div>
      <header className="bg-white border-b border-slate-100 sticky top-0 z-[700]">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center gap-2 sm:gap-4">
          <Link to="/" aria-label="Blood Bridge home"><Logo /></Link>
          <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
            <Link to="/emergency" aria-label="Emergency Help" className="inline-flex whitespace-nowrap btn btn-sm px-2 sm:px-3 bg-red-50 text-red-700 border border-red-200 hover:bg-red-100">
              <Siren className="w-4 h-4" /><span className="hidden sm:inline">Emergency Help</span>
            </Link>
            <Link to="/create-request" aria-label="Request Blood" className="inline-flex whitespace-nowrap btn-primary btn-sm px-2 sm:px-3">
              <Droplet className="w-4 h-4 fill-white" /><span className="hidden sm:inline">Request Blood</span>
            </Link>
            {user ? (
              <>
                <NotificationBell />
                <Link to={DASHBOARD_PATH[user.role]} className="hidden md:inline-flex whitespace-nowrap btn-ghost btn-sm">
                  <LayoutDashboard className="w-4 h-4" /> My Dashboard
                </Link>
                <button onClick={() => { logout(); nav('/') }} className="hidden lg:inline-flex p-2 text-slate-500 hover:text-blood-600" aria-label="Log out" title="Log out">
                  <LogOut className="w-5 h-5" />
                </button>
              </>
            ) : (
              <span className="hidden md:flex items-center gap-1">
                <Link to="/login" className="px-3 py-2 text-sm font-medium text-slate-700 hover:text-navy-900">Login</Link>
                <Link to="/register" className="btn-primary btn-sm">Register</Link>
              </span>
            )}
            <button className="lg:hidden p-1.5 sm:p-2 text-slate-700" onClick={() => setOpen((o) => !o)} aria-label="Menu" aria-expanded={open}>
              {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
        <nav className="hidden lg:block border-t border-slate-100 bg-slate-50/60" aria-label="Main">
          <div className="max-w-7xl mx-auto px-4 h-11 flex items-center gap-1">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} className={linkCls}>
                {n.icon && <n.icon className="inline w-4 h-4 mr-1 -mt-0.5 text-blood-600 fill-blood-600" />}{n.label}
              </NavLink>
            ))}
            <Link to="/#how-it-works" className="ml-auto px-2.5 py-2 text-xs font-medium text-slate-500 hover:text-navy-900 whitespace-nowrap">How it works</Link>
          </div>
        </nav>
        {open && (
          <nav className="lg:hidden border-t border-slate-100 bg-white px-4 py-3 grid gap-1" aria-label="Mobile">
            <NavLink to="/create-request" className={linkCls}>Request Blood</NavLink>
            {NAV.map((n) => <NavLink key={n.to} to={n.to} className={linkCls}>{n.label}</NavLink>)}
            <NavLink to="/emergency" className={linkCls}>Emergency Help</NavLink>
            {user ? (
              <>
                <NavLink to={DASHBOARD_PATH[user.role]} className={linkCls}>My Dashboard</NavLink>
                <NavLink to="/notifications" className={linkCls}>Notifications</NavLink>
                <button onClick={() => { logout(); nav('/') }} className="text-left px-3 py-2 text-sm text-slate-600">Log out</button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={linkCls}>Login</NavLink>
                <NavLink to="/register" className={linkCls}>Register</NavLink>
              </>
            )}
          </nav>
        )}
      </header>
      <main className="flex-1"><Outlet /></main>
      <footer className="bg-navy-950 text-slate-400">
        <div className="max-w-7xl mx-auto px-4 py-8 flex flex-col md:flex-row gap-4 justify-between items-start md:items-center text-sm">
          <span className="flex items-center gap-2 font-black text-white"><HeartPulse className="w-5 h-5 text-blood-600" /> BLOOD BRIDGE</span>
          <span className="flex flex-wrap gap-4">
            <Link to="/donate" className="hover:text-white">Donation guide</Link>
            <Link to="/emergency" className="hover:text-white">Emergency help</Link>
            <a href="https://www.openstreetmap.org/copyright" className="hover:text-white" target="_blank" rel="noreferrer">Map data © OpenStreetMap</a>
          </span>
          <span>© {new Date().getFullYear()} BLOOD BRIDGE. Real-Time Blood Request &amp; Donor Matching System.</span>
        </div>
      </footer>
    </div>
  )
}
