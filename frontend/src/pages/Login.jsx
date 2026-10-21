import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Droplet, Lock, Mail, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../lib/api'
import { DASHBOARD_PATH } from '../lib/blood'
import { ErrorBox } from '../components/ui'

const ROLES = ['DONOR', 'PATIENT', 'HOSPITAL', 'ADMIN']

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [role, setRole] = useState('DONOR')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setErr(''); setBusy(true)
    try {
      const me = await login(email.trim(), password, role)
      nav(loc.state?.from || DASHBOARD_PATH[me.role], { replace: true })
    } catch (e2) {
      setErr(errorMessage(e2, 'Login failed. Please try again.'))
    } finally { setBusy(false) }
  }

  return (
    <div className="bg-slate-50 min-h-[calc(100vh-7rem)] py-12 px-4">
      <form onSubmit={submit} className="card max-w-md mx-auto p-8 shadow-xl" noValidate>
        <div className="w-14 h-14 rounded-2xl bg-blood-600 mx-auto flex items-center justify-center shadow-lg shadow-blood-600/30">
          <Droplet className="w-6 h-6 text-white fill-white" />
        </div>
        <h1 className="text-2xl font-black text-center text-navy-900 mt-4">Login to Blood Bridge</h1>
        <p className="text-xs text-center text-slate-500 mt-1">Access your dashboard to match requests or manage inventory</p>

        <p className="label mt-6">Select your role</p>
        <div className="grid grid-cols-4 gap-2" role="radiogroup">
          {ROLES.map((r) => (
            <button type="button" key={r} role="radio" aria-checked={role === r} onClick={() => setRole(r)}
                    className={`rounded-xl py-2 text-[11px] font-bold border transition ${role === r ? 'bg-blood-600 text-white border-blood-600' : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'}`}>
              {r}
            </button>
          ))}
        </div>

        <label className="label mt-5" htmlFor="email">Email address</label>
        <div className="relative">
          <Mail className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input id="email" type="email" autoComplete="email" required className="input pl-10" placeholder="name@example.com"
                 value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <label className="label mt-4" htmlFor="password">Password</label>
        <div className="relative">
          <Lock className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input id="password" type="password" autoComplete="current-password" required className="input pl-10" placeholder="••••••••"
                 value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>

        <div className="mt-5"><ErrorBox message={err} /></div>
        <button className="btn-primary w-full mt-5" disabled={busy || !email || !password}>
          {busy && <Loader2 className="w-4 h-4 animate-spin" />} Sign In
        </button>
        <p className="text-center text-xs text-slate-500 mt-6">Don&apos;t have an account? <Link to="/register" className="font-bold text-blood-600">Register here</Link></p>
      </form>
    </div>
  )
}
