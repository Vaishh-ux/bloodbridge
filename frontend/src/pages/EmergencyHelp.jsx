import { Link } from 'react-router-dom'
import { Truck, Building2, Droplet, Phone, Siren, Users } from 'lucide-react'
import { PageHeader } from '../components/ui'

const NUMBERS = [
  { n: '112', t: 'National emergency number', d: 'Police, fire and medical emergencies across India.' },
  { n: '108', t: 'Emergency ambulance', d: 'Toll-free emergency ambulance service in most states.' },
  { n: '102', t: 'Maternal & newborn transport', d: 'Truck for pregnant women and newborns to government hospitals.' },
]

export default function EmergencyHelp() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <PageHeader icon={Siren} title="Emergency Help" subtitle="What to do first when someone urgently needs blood." />
      <div className="rounded-3xl bg-red-600 text-white p-6 sm:p-8">
        <p className="text-xl font-black">If a life is in immediate danger, call emergency services first.</p>
        <div className="grid sm:grid-cols-3 gap-4 mt-6">
          {NUMBERS.map((x) => (
            <a key={x.n} href={`tel:${x.n}`} className="rounded-2xl bg-white/10 hover:bg-white/20 border border-white/20 p-4 block">
              <p className="text-3xl font-black flex items-center gap-2"><Phone className="w-6 h-6" />{x.n}</p>
              <p className="font-bold mt-1">{x.t}</p><p className="text-sm text-red-100">{x.d}</p>
            </a>
          ))}
        </div>
        <p className="text-xs text-red-100 mt-4">Numbers apply in India. Availability can vary by state; outside India use your local emergency number.</p>
      </div>

      <h2 className="text-2xl font-black text-navy-900 mt-10">Getting blood quickly</h2>
      <ol className="mt-4 grid gap-4">
        {[
          { i: Building2, t: 'Talk to the treating hospital’s blood bank', d: 'They know the exact component needed (whole blood, red cells, platelets, plasma), will crossmatch, and can arrange replacement donors or stock from nearby banks.' },
          { i: Droplet, t: 'Post a request on Blood Bridge', d: 'Compatible, available donors within range are alerted instantly. Keep the request details accurate and cancel it once the need is met.' },
          { i: Building2, t: 'Check nearby blood banks', d: 'See registered facilities and any stock they report, then call before travelling. The Government of India eRaktKosh portal also lists blood bank stock.' },
          { i: Users, t: 'Reach your own network', d: 'Family, friends, colleagues and community groups with compatible blood groups are often the fastest donors.' },
          { i: Truck, t: 'Keep the patient’s details ready', d: 'Blood group report, hospital name and ward, units and component required, and a reachable phone number at the hospital.' },
        ].map((s, k) => (
          <li key={k} className="card p-5 flex gap-4">
            <span className="w-10 h-10 rounded-xl bg-blood-50 text-blood-600 flex items-center justify-center font-black shrink-0">{k + 1}</span>
            <div><p className="font-black text-navy-900 flex items-center gap-2"><s.i className="w-4 h-4 text-blood-600" />{s.t}</p><p className="text-sm text-slate-600 mt-1">{s.d}</p></div>
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap gap-3 mt-8">
        <Link to="/create-request" className="btn-primary"><Droplet className="w-4 h-4 fill-white" /> Request blood</Link>
        <Link to="/blood-banks" className="btn-dark">Find blood banks</Link>
        <Link to="/requests" className="btn-ghost">See urgent requests</Link>
      </div>
      <p className="text-xs text-slate-500 mt-8">Blood Bridge is a coordination tool and does not provide medical advice. Never delay emergency care while searching for donors.</p>
    </div>
  )
}
