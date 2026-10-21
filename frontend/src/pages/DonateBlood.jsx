import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarClock, ClipboardCheck, Coffee, Heart, HeartPulse, ShieldAlert } from 'lucide-react'
import api from '../lib/api'
import { PageHeader } from '../components/ui'
import { DISCLAIMER } from '../components/Layout'
import { useAuth } from '../context/AuthContext'

function Section({ icon: Icon, title, items }) {
  return (
    <div className="card p-6">
      <h2 className="font-black text-navy-900 flex items-center gap-2"><Icon className="w-5 h-5 text-blood-600" />{title}</h2>
      <ul className="mt-3 space-y-2 text-sm text-slate-600 list-disc pl-5">{items.map((t) => <li key={t}>{t}</li>)}</ul>
    </div>
  )
}

export default function DonateBlood() {
  const { user } = useAuth()
  const [cfg, setCfg] = useState(null)
  useEffect(() => { api.get('/stats/config').then((r) => setCfg(r.data)).catch(() => {}) }, [])
  const interval = cfg?.min_donation_interval_days ?? 90

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <PageHeader icon={Heart} title="Donate Blood" subtitle="Who can donate, how to prepare, and how to look after yourself afterwards.">
        {user?.role === 'DONOR'
          ? <Link to="/donor-dashboard" className="btn-primary">Go to my donor dashboard</Link>
          : <Link to="/register?role=DONOR" className="btn-primary"><Heart className="w-4 h-4 fill-white" /> Become a donor</Link>}
      </PageHeader>

      <div className="grid md:grid-cols-2 gap-6">
        <Section icon={ClipboardCheck} title="General eligibility (India)" items={[
          'Age 18–65 years.',
          'Body weight at least 45 kg.',
          'Haemoglobin at least 12.5 g/dL (checked at the blood bank before donating).',
          'Feeling well on the day, with no fever, cold or active infection.',
          'Temporary deferral is common after recent illness, surgery, tattoos/piercings, some vaccines, pregnancy or breastfeeding, and certain medicines — the blood bank will advise.',
        ]} />
        <Section icon={CalendarClock} title="Donation interval" items={[
          `Blood Bridge only matches donors whose last whole-blood donation was at least ${interval} days ago (configurable system setting).`,
          'Indian guidance requires a gap of more than 90 days between whole-blood donations; your blood bank may ask for longer.',
          'Platelet and plasma (apheresis) donations follow different intervals set by the blood bank.',
          'After a confirmed donation your Blood Bridge status is set to “unavailable” — switch it back on when you are eligible again.',
        ]} />
        <Section icon={Coffee} title="Before you donate" items={[
          'Sleep well the night before.',
          'Eat a light, non-fatty meal 2–3 hours before; do not donate on an empty stomach.',
          'Drink plenty of water; avoid alcohol for 24 hours before.',
          'Carry a photo ID and a list of any medicines you take.',
          'Answer the screening questionnaire honestly — it protects you and the patient.',
        ]} />
        <Section icon={HeartPulse} title="Aftercare" items={[
          'Rest for 10–15 minutes and have the refreshments offered.',
          'Drink extra fluids for the next 24–48 hours.',
          'Keep the bandage on for a few hours; avoid heavy lifting or strenuous exercise for the rest of the day.',
          'If you feel dizzy, lie down with your feet raised.',
          'Contact the blood bank if you feel unwell afterwards or remember health information you did not mention.',
        ]} />
      </div>

      <div className="mt-6 rounded-2xl bg-amber-50 border border-amber-200 p-5 text-sm text-amber-900 flex gap-3">
        <ShieldAlert className="w-5 h-5 shrink-0" />
        <div>
          <p className="font-bold">Medical disclaimer</p>
          <p className="mt-1">{DISCLAIMER} This page is general information, not medical advice; criteria are based on Indian national guidance and may differ by blood bank or country.</p>
        </div>
      </div>
    </div>
  )
}
