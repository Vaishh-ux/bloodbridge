import { useEffect, useState } from 'react'
import { Building2, Crosshair, MapPin, Navigation, Phone, ShieldCheck } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { BLOOD_GROUPS, COMPONENTS, timeAgo } from '../lib/blood'
import { currentPosition, directionsUrl } from '../lib/geo'
import { EmergencyMap } from '../components/MapView'
import { Empty, ErrorBox, PageHeader, Skeleton } from '../components/ui'

function StockTable({ rows, updated }) {
  const present = COMPONENTS.filter((c) => rows.some((r) => r.component === c.key))
  const cell = (c, g) => rows.find((r) => r.component === c && r.blood_group === g)
  return (
    <div className="mt-4">
      <div className="overflow-x-auto">
        <table className="w-full text-xs min-w-[520px]">
          <thead><tr className="text-slate-500">
            <th className="text-left font-bold uppercase p-1.5">Component</th>
            {BLOOD_GROUPS.map((g) => <th key={g} className="font-black text-blood-600 p-1.5">{g}</th>)}
          </tr></thead>
          <tbody>
            {present.map((c) => (
              <tr key={c.key} className="border-t border-slate-100">
                <td className="p-1.5 font-bold text-slate-700 whitespace-nowrap">{c.label}</td>
                {BLOOD_GROUPS.map((g) => {
                  const r = cell(c.key, g)
                  const tone = !r ? 'text-slate-300' : r.status === 'OUT' ? 'text-slate-400' : r.status === 'LOW' ? 'text-amber-600 font-black' : 'text-emerald-700 font-black'
                  return <td key={g} className={`p-1.5 text-center text-sm ${tone}`} title={r ? `${r.available_units} available, ${r.reserved_units} reserved` : 'Not reported'}>{r ? r.available_units : '—'}</td>
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-slate-400 mt-1">Available units reported by the verified facility · updated {timeAgo(updated)} · “—” = not reported. Call to confirm before travelling.</p>
    </div>
  )
}

export default function BloodBanks() {
  const [f, setF] = useState({ city: '', facility_type: '', blood_group: '' })
  const [me, setMe] = useState(null)
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState('')

  const load = async () => {
    setErr('')
    try {
      const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v))
      if (me) Object.assign(params, { lat: me.lat, lng: me.lng })
      const { data } = await api.get('/hospitals', { params })
      setRows(data)
    } catch (e) { setErr(errorMessage(e)); setRows([]) }
  }
  useEffect(() => { load() }, [me]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <PageHeader icon={Building2} title="Find Blood Banks & Hospitals" subtitle="Registered facilities, their contact details and the blood stock they report.">
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); load() }}>
          <input className="input py-2 w-36" placeholder="City" value={f.city} onChange={(e) => setF({ ...f, city: e.target.value })} aria-label="City" />
          <select className="input py-2 w-auto" value={f.facility_type} onChange={(e) => setF({ ...f, facility_type: e.target.value })} aria-label="Type">
            <option value="">All facilities</option><option value="HOSPITAL">Hospitals</option><option value="BLOOD_BANK">Blood banks</option>
          </select>
          <select className="input py-2 w-auto font-bold text-blood-600" value={f.blood_group} onChange={(e) => setF({ ...f, blood_group: e.target.value })} aria-label="Stock for">
            <option value="">Any stock</option>{BLOOD_GROUPS.map((g) => <option key={g} value={g}>Red cells for {g} patient</option>)}
          </select>
          <button className="btn-primary btn-sm">Search</button>
          <button type="button" className="btn-ghost btn-sm" onClick={() => currentPosition().then(setMe).catch((e) => setErr(e.message))}><Crosshair className="w-4 h-4" /> Nearest</button>
        </form>
      </PageHeader>
      <ErrorBox message={err} onRetry={load} />
      {rows === null ? <Skeleton /> : rows.length === 0 ? (
        <Empty title="No facilities found">No registered hospital or blood bank matches these filters yet. Facilities can register from the Register page. You can also check the Government of India eRaktKosh portal for blood bank stock.</Empty>
      ) : (
        <div className="grid lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3 space-y-4 min-w-0">
            {rows.map((h) => (
              <article key={h.id} className="card p-5 min-w-0">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-black text-navy-900 flex items-center gap-2">{h.name}
                      {h.verified ? <span className="chip bg-emerald-50 text-emerald-700"><ShieldCheck className="w-3 h-3" />Verified</span>
                                  : <span className="chip bg-slate-100 text-slate-500">Unverified</span>}</p>
                    <p className="text-xs font-bold text-slate-400 uppercase mt-0.5">{h.facility_type === 'BLOOD_BANK' ? 'Blood bank' : 'Hospital'}{h.distance_km != null && ` · ${h.distance_km} km away`}</p>
                  </div>
                  <div className="flex gap-2">
                    <a href={`tel:${h.phone}`} className="btn-ghost btn-sm"><Phone className="w-4 h-4" /> Call</a>
                    {h.latitude != null && <a href={directionsUrl(h.latitude, h.longitude)} target="_blank" rel="noreferrer" className="btn-dark btn-sm"><Navigation className="w-4 h-4" /> Directions</a>}
                  </div>
                </div>
                <p className="text-sm text-slate-600 mt-2 flex gap-1"><MapPin className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />{h.address}, {h.city}, {h.state} {h.pincode || ''}</p>
                {h.inventory_reported ? <StockTable rows={h.inventory} updated={h.inventory_last_updated} />
                  : h.stock_hidden_until_verified
                    ? <p className="text-xs text-amber-700 bg-amber-50 rounded-xl p-2 mt-3">Stock reported by this facility will be shown once a Blood Bridge administrator verifies it. Please call to check availability.</p>
                    : <p className="text-xs text-slate-400 mt-3">This facility has not reported stock on Blood Bridge. Please call to check availability.</p>}
              </article>
            ))}
          </div>
          <div className="lg:col-span-2 lg:sticky lg:top-32 h-fit min-w-0"><EmergencyMap facilities={rows} me={me} height={520} /></div>
        </div>
      )}
    </div>
  )
}
