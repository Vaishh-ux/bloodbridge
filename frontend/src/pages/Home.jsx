import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Activity, Award, Building2, CheckCircle2, Droplet, Heart, Users, Siren, BellRing, Cpu, ClipboardCheck, LayoutDashboard } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { BLOOD_GROUPS, DASHBOARD_PATH, canDonateTo, canReceiveFrom } from '../lib/blood'
import { useAuth } from '../context/AuthContext'

function HeroStat({ icon: Icon, tone, value, label, wide }) {
  return (
    <div className={`rounded-3xl bg-white/5 border border-white/10 backdrop-blur p-6 text-center ${wide ? 'col-span-2' : ''}`}>
      <Icon className={`w-7 h-7 mx-auto ${tone}`} />
      <p className="mt-3 text-3xl font-black text-white">{value ?? '—'}</p>
      <p className="mt-1 text-[11px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
    </div>
  )
}

export default function Home() {
  const [stats, setStats] = useState(null)
  const [err, setErr] = useState('')
  const { user } = useAuth()
  const { hash } = useLocation()
  useEffect(() => {
    if (hash) setTimeout(() => document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: 'smooth' }), 50)
  }, [hash])
  const quick = [
    { to: '/donate', icon: Heart, title: 'Donate Blood', text: 'Eligibility, preparation & sign up', tone: 'text-blood-600 bg-blood-50' },
    { to: '/blood-banks', icon: Building2, title: 'Find Blood Banks', text: 'Nearby stock, contacts & directions', tone: 'text-sky-600 bg-sky-50' },
    { to: '/emergency', icon: Siren, title: 'Emergency Help', text: 'What to do first · 112 / 108', tone: 'text-red-700 bg-red-50' },
    { to: user ? DASHBOARD_PATH[user.role] : '/login', icon: LayoutDashboard, title: 'My Dashboard', text: user ? `Signed in as ${user.name}` : 'Log in to track requests & matches', tone: 'text-slate-700 bg-slate-100' },
  ]
  useEffect(() => {
    api.get('/stats/public').then((r) => setStats(r.data)).catch((e) => setErr(errorMessage(e)))
  }, [])
  const fmt = (n) => (stats ? n.toLocaleString('en-IN') : '…')

  const steps = [
    { n: 1, title: 'Create Request', icon: ClipboardCheck, tone: 'bg-blood-50 text-blood-600', text: 'Patient or hospital submits an emergency blood request specifying blood group, units, and hospital location.' },
    { n: 2, title: 'Matching Engine', icon: Cpu, tone: 'bg-sky-50 text-sky-600', text: 'Engine checks red-cell compatibility, Haversine distance and screening criteria, then ranks the nearest donors.' },
    { n: 3, title: 'Instant Alert', icon: BellRing, tone: 'bg-amber-50 text-amber-600', text: 'Matched donors receive real-time in-app alerts over WebSockets and can accept or decline the request.' },
    { n: 4, title: 'Donation Confirmed', icon: CheckCircle2, tone: 'bg-emerald-50 text-emerald-600', text: 'The hospital confirms the donation, the request is closed, and the donor’s history is updated.' },
  ]

  return (
    <>
      <section className="relative overflow-hidden bg-navy-950">
        <div className="absolute -top-40 -right-40 w-[36rem] h-[36rem] rounded-full bg-blood-600/20 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-[30rem] h-[30rem] rounded-full bg-blood-600/10 blur-3xl" />
        <div className="relative max-w-7xl mx-auto px-4 py-16 lg:py-24 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-blood-600/40 bg-blood-600/10 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-white">
              <Droplet className="w-4 h-4 fill-white" /> Real-Time Blood &amp; Donor Network
            </span>
            <h1 className="mt-6 text-5xl sm:text-6xl font-black tracking-tight text-white leading-[1.05]">
              Every Drop<br /><span className="text-blood-600">Connects a Life.</span>
            </h1>
            <p className="mt-6 text-lg text-slate-300 max-w-xl">
              Blood Bridge connects patients, hospitals, and eligible blood donors in real time using automated location
              proximity matching and red blood cell compatibility scoring.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Link to="/create-request" className="btn-primary px-7 py-4 text-base"><Droplet className="w-5 h-5 fill-white" /> Request Blood Now</Link>
              <Link to="/register?role=DONOR" className="btn px-7 py-4 text-base bg-white/10 text-white border border-white/15 hover:bg-white/15">
                <Heart className="w-5 h-5 fill-blood-500 text-blood-500" /> Become a Donor
              </Link>
            </div>
            <Link to="/emergency" className="mt-6 inline-flex items-center gap-2 text-sm text-amber-300 hover:text-amber-200">
              <Siren className="w-4 h-4" /> Life-threatening emergency? Call 112 / 108 first →
            </Link>
          </div>
          <div>
            <div className="grid grid-cols-2 gap-4">
              <HeroStat icon={Users} tone="text-blood-500" value={fmt(stats?.registered_donors)} label="Registered Donors" />
              <HeroStat icon={Heart} tone="text-emerald-400" value={fmt(stats?.available_donors)} label="Available Donors" />
              <HeroStat icon={Activity} tone="text-amber-400" value={fmt(stats?.active_requests)} label="Active Requests" />
              <HeroStat icon={Award} tone="text-sky-400" value={fmt(stats?.fulfilled_requests)} label="Fulfilled Requests" />
              <HeroStat icon={Building2} tone="text-slate-300" wide
                        value={stats ? `${stats.hospitals} hospital${stats.hospitals === 1 ? '' : 's'} · ${stats.blood_banks} blood bank${stats.blood_banks === 1 ? '' : 's'}` : '…'}
                        label="Participating facilities" />
            </div>
            <p className="mt-3 text-xs text-slate-500 text-center">
              {err ? `Live statistics unavailable: ${err}` : 'Live counts from the Blood Bridge database.'}
            </p>
          </div>
        </div>
      </section>

      <section aria-label="Quick navigation" className="relative z-10 -mt-10">
        <div className="max-w-7xl mx-auto px-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-[minmax(0,1.35fr)_repeat(4,minmax(0,1fr))]">
          <Link to="/create-request" className="sm:col-span-2 xl:col-span-1 rounded-3xl bg-blood-600 text-white p-5 shadow-xl shadow-blood-600/30 hover:bg-blood-700 transition flex items-center gap-4">
            <span className="w-14 h-14 rounded-2xl bg-white/15 flex items-center justify-center shrink-0"><Droplet className="w-7 h-7 fill-white" /></span>
            <span className="min-w-0"><span className="block text-lg font-black leading-tight">Emergency Blood Request</span>
              <span className="block text-xs text-red-100 mt-0.5">One form · alerts compatible donors instantly</span></span>
          </Link>
          {quick.map((q) => (
            <Link key={q.title} to={q.to} className="card p-4 min-w-0 hover:shadow-md hover:border-blood-200 transition flex items-center gap-3">
              <span className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${q.tone}`}><q.icon className="w-5 h-5" /></span>
              <span className="min-w-0"><span className="block font-black text-navy-900">{q.title}</span><span className="block text-xs text-slate-500 truncate">{q.text}</span></span>
            </Link>
          ))}
        </div>
      </section>

      <section id="how-it-works" className="bg-slate-50 py-20 -mt-6">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-4xl font-black text-center text-navy-900">How Blood Bridge Works</h2>
          <p className="text-center text-slate-500 mt-3">Our automated donor matching engine pairs emergency requests with compatible nearby donors instantly.</p>
          <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((s) => (
              <div key={s.n} className="card p-6">
                <span className={`w-11 h-11 rounded-xl flex items-center justify-center font-black ${s.tone}`}>{s.n}</span>
                <h3 className="mt-4 font-black text-navy-900">{s.title}</h3>
                <p className="mt-2 text-sm text-slate-500">{s.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-4xl font-black text-center text-navy-900">Blood Group Compatibility Rules</h2>
          <p className="text-center text-slate-500 mt-3">Transfusion rules based on Red Blood Cell (RBC) antigen-antibody compatibility.</p>
          <div className="mt-10 card overflow-x-auto">
            <table className="w-full text-sm min-w-[560px]">
              <thead className="bg-navy-950 text-white text-xs uppercase tracking-wide">
                <tr><th className="text-left p-4">Blood Group</th><th className="text-left p-4">Can Donate To</th><th className="text-left p-4">Can Receive From</th></tr>
              </thead>
              <tbody>
                {['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'].map((g) => (
                  <tr key={g} className="border-t border-slate-100">
                    <td className="p-4"><span className="chip bg-blood-50 text-blood-600 text-sm">{g}</span></td>
                    <td className="p-4 font-medium text-slate-700">{g === 'O-' ? 'EVERYONE (Universal Donor)' : g === 'AB+' ? 'AB+ ONLY' : canDonateTo(g).join(', ')}</td>
                    <td className="p-4 font-medium text-slate-700">{g === 'AB+' ? 'EVERYONE (Universal Recipient)' : canReceiveFrom(g).join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500 mt-3 text-center">
            Red-cell compatibility only. Plasma and platelet rules differ, and every transfusion still requires laboratory crossmatching.
          </p>
          <div className="mt-12 grid md:grid-cols-3 gap-6">
            {[
              { to: '/find-donors', t: 'Find compatible donors', d: `Search ${BLOOD_GROUPS.length} blood groups by city, PIN code or distance.` },
              { to: '/blood-banks', t: 'Find blood banks', d: 'Registered hospitals and blood banks with the stock they report.' },
              { to: '/donate', t: 'Donation guide', d: 'Eligibility, preparation, donation interval and aftercare.' },
            ].map((c) => (
              <Link key={c.to} to={c.to} className="card p-6 hover:border-blood-200 hover:shadow-md transition">
                <p className="font-black text-navy-900">{c.t} →</p><p className="text-sm text-slate-500 mt-1">{c.d}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
