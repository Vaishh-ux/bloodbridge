import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Building2, CheckCircle2, Clock, Droplet, History, Package, Phone, Save, Siren } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { BLOOD_GROUPS, COMPONENTS, RED_CELL_COMPONENTS, canReceiveFrom, componentLabel, timeAgo } from '../lib/blood'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useRealtimeEvent } from '../context/RealtimeContext'
import { MatchesModal } from './PatientDashboard'
import { ErrorBox, Modal, PageHeader, Spinner, StatCard, StatusBadge, UrgencyBadge } from '../components/ui'

function InventoryPanel({ hospitalId }) {
  const toast = useToast()
  const [comp, setComp] = useState('WHOLE_BLOOD')
  const [rows, setRows] = useState(null)
  const [draft, setDraft] = useState({})
  const [reason, setReason] = useState('')
  const [history, setHistory] = useState(null)
  const [busy, setBusy] = useState(false)
  const key = (c, g) => `${c}|${g}`
  const find = (c, g) => rows?.find((x) => x.component === c && x.blood_group === g)

  const load = useCallback(async () => {
    const { data } = await api.get(`/hospitals/${hospitalId}/inventory`)
    setRows(data)
    const d = {}
    COMPONENTS.forEach(({ key: c }) => BLOOD_GROUPS.forEach((g) => {
      const r = data.find((x) => x.component === c && x.blood_group === g)
      d[`${c}|${g}`] = { available_units: r ? r.available_units : '', reserved_units: r ? r.reserved_units : '' }
    }))
    setDraft(d)
  }, [hospitalId])
  useEffect(() => {
    load().catch(() => setRows([]))
    const onChange = () => load().catch(() => {})
    window.addEventListener('bb:inventory', onChange)
    return () => window.removeEventListener('bb:inventory', onChange)
  }, [load])

  const changed = rows ? COMPONENTS.flatMap(({ key: c }) => BLOOD_GROUPS.map((g) => [c, g])).filter(([c, g]) => {
    const r = find(c, g)
    const d = draft[key(c, g)]
    if (!d || d.available_units === '') return false
    return !r || +d.available_units !== r.available_units || +(d.reserved_units || 0) !== r.reserved_units
  }) : []

  const save = async () => {
    setBusy(true)
    try {
      for (const [c, g] of changed) {
        const d = draft[key(c, g)]
        if (+d.available_units < 0 || +(d.reserved_units || 0) < 0) throw new Error('Units cannot be negative.')
        await api.put(`/hospitals/${hospitalId}/inventory`, {
          blood_group: g, component: c, available_units: +d.available_units, reserved_units: +(d.reserved_units || 0), reason: reason || 'Stock update',
        })
      }
      toast.success(`Saved ${changed.length} stock line(s).`); setReason(''); await load()
    } catch (e) { toast.error(e.message === 'Units cannot be negative.' ? e.message : errorMessage(e)) } finally { setBusy(false) }
  }
  const showHistory = async () => {
    try { const { data } = await api.get(`/hospitals/${hospitalId}/inventory/history`); setHistory(data) } catch (e) { toast.error(errorMessage(e)) }
  }

  if (!rows) return <Spinner />
  const countFor = (c) => rows.filter((r) => r.component === c).reduce((a, r) => a + r.available_units, 0)
  const pendingFor = (c) => changed.filter(([cc]) => cc === c).length
  return (
    <section className="card p-6">
      <div className="flex flex-wrap justify-between gap-3 items-center">
        <div>
          <h2 className="font-black text-navy-900 flex items-center gap-2"><Package className="w-5 h-5 text-blood-600" />Blood Inventory</h2>
          <p className="text-xs text-slate-500">
            {rows.length === 0 ? 'No stock reported yet — enter your current units below.' : 'Units you report by component and blood group.'}
            {' '}Stock is shown publicly on “Find Blood Banks” only after an administrator verifies your facility.
          </p>
        </div>
        <button className="btn-ghost btn-sm" onClick={showHistory}><History className="w-4 h-4" />Inventory history</button>
      </div>
      <div className="flex flex-wrap gap-2 mt-5" role="tablist" aria-label="Blood component">
        {COMPONENTS.map((c) => (
          <button key={c.key} role="tab" aria-selected={comp === c.key} onClick={() => setComp(c.key)}
                  className={`btn btn-sm ${comp === c.key ? 'bg-navy-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            {c.label}
            <span className={`text-[10px] rounded-full px-1.5 ${comp === c.key ? 'bg-white/20' : 'bg-white'}`}>{countFor(c.key)}</span>
            {pendingFor(c.key) > 0 && <span className="w-2 h-2 rounded-full bg-amber-400" title="Unsaved changes" />}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
        {BLOOD_GROUPS.map((g) => {
          const r = find(comp, g)
          const k = key(comp, g)
          const tone = !r ? 'border-slate-100' : r.status === 'OUT' ? 'border-red-200 bg-red-50/50' : r.status === 'LOW' ? 'border-amber-200 bg-amber-50/50' : 'border-emerald-100'
          return (
            <div key={k} className={`rounded-2xl border p-3 ${tone}`}>
              <div className="flex justify-between items-center"><span className="font-black text-blood-600">{g}</span>
                {r && r.status !== 'OK' && <span className="chip bg-white text-red-600"><AlertTriangle className="w-3 h-3" />{r.status === 'OUT' ? 'Out' : 'Low'}</span>}</div>
              <label className="text-[10px] font-bold uppercase text-slate-500 mt-2 block">Available units
                <input type="number" min={0} className="input py-2 mt-1" value={draft[k]?.available_units ?? ''} placeholder="—"
                       aria-label={`${componentLabel(comp)} ${g} available units`}
                       onChange={(e) => setDraft({ ...draft, [k]: { ...draft[k], available_units: e.target.value } })} /></label>
              <label className="text-[10px] font-bold uppercase text-slate-500 mt-2 block">Reserved units
                <input type="number" min={0} className="input py-2 mt-1" value={draft[k]?.reserved_units ?? ''} placeholder="0"
                       aria-label={`${componentLabel(comp)} ${g} reserved units`}
                       onChange={(e) => setDraft({ ...draft, [k]: { ...draft[k], reserved_units: e.target.value } })} /></label>
              {r && <p className="text-[10px] text-slate-400 mt-1">Updated {timeAgo(r.last_updated)}</p>}
            </div>
          )
        })}
      </div>
      <div className="flex flex-col sm:flex-row gap-2 mt-4">
        <input className="input" placeholder="Reason (e.g. Daily count, expired units removed, camp collection)" value={reason} onChange={(e) => setReason(e.target.value)} />
        <button className="btn-primary whitespace-nowrap" disabled={busy || changed.length === 0} onClick={save}><Save className="w-4 h-4" />Save Stock Changes{changed.length ? ` (${changed.length})` : ''}</button>
      </div>
      <Modal open={!!history} title="Inventory history" onClose={() => setHistory(null)}>
        {history?.length === 0 ? <p className="text-sm text-slate-500">No changes recorded yet.</p> : (
          <table className="w-full text-sm">
            <thead className="text-xs uppercase text-slate-500"><tr><th className="text-left p-2">When</th><th className="text-left p-2">Item</th><th className="text-left p-2">Change</th><th className="text-left p-2">After</th><th className="text-left p-2">Reason</th></tr></thead>
            <tbody>{history?.map((h) => (
              <tr key={h.id} className="border-t border-slate-100"><td className="p-2">{timeAgo(h.created_at)}</td><td className="p-2"><span className="font-bold text-blood-600">{h.blood_group}</span> <span className="text-slate-500">{h.component_label}</span></td>
                <td className={`p-2 font-bold ${h.available_change < 0 ? 'text-red-600' : 'text-emerald-600'}`}>{h.available_change > 0 ? '+' : ''}{h.available_change}</td><td className="p-2">{h.available_after}</td><td className="p-2 text-slate-500">{h.reason}</td></tr>
            ))}</tbody>
          </table>
        )}
      </Modal>
    </section>
  )
}

export default function HospitalDashboard() {
  const { user } = useAuth()
  const toast = useToast()
  const hid = user.profile?.profile_id
  const [reqs, setReqs] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(null)
  const [view, setView] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const [stock, setStock] = useState(null)

  const load = useCallback(async () => {
    try { const { data } = await api.get(`/hospitals/${hid}/requests`); setReqs(data); setErr('') } catch (e) { setErr(errorMessage(e)) }
  }, [hid])
  useEffect(() => { if (hid) load() }, [hid, load])
  useRealtimeEvent(load, ['NOTIFICATION_NEW', 'REQUEST_UPDATED', 'REQUEST_NEW'])

  const act = async (key, fn, confirmText) => {
    if (confirmText && !window.confirm(confirmText)) return false
    setBusy(key)
    try { const r = await fn(); toast.success(r.data.message || 'Done.'); await load(); return true }
    catch (e) { toast.error(errorMessage(e)); return false } finally { setBusy(null) }
  }

  if (!hid) return <div className="p-8"><ErrorBox message="Facility profile not found for this account." /></div>
  const active = reqs?.filter((r) => !['COMPLETED', 'CANCELLED'].includes(r.status)) || []

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <PageHeader icon={Building2} title={user.profile.name}
                  subtitle={`${user.profile.facility_type === 'BLOOD_BANK' ? 'Blood bank' : 'Hospital'} · ${user.profile.city} · ${user.profile.verified ? 'Verified by Blood Bridge admin' : 'Awaiting admin verification'}`}>
        <Link to="/create-request" className="btn-primary"><Droplet className="w-4 h-4 fill-white" />Create Blood Request</Link>
      </PageHeader>
      {!user.profile.verified && <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-2xl p-4">Your facility is listed as <strong>unverified</strong> until an administrator verifies it. You can still create requests and manage stock.</p>}
      <ErrorBox message={err} onRetry={load} />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Droplet} label="Total requests" value={reqs?.length} />
        <StatCard icon={Clock} label="Pending requests" value={active.length} tone="text-amber-500" />
        <StatCard icon={Siren} label="Critical (active)" value={active.filter((r) => r.emergency_level === 'Critical').length} tone="text-red-600" />
        <StatCard icon={CheckCircle2} label="Completed" value={reqs?.filter((r) => r.status === 'COMPLETED').length} tone="text-emerald-500" />
      </div>

      <InventoryPanel hospitalId={hid} />

      <section className="card p-6">
        <h2 className="font-black text-navy-900">Requests at this facility</h2>
        <p className="text-xs text-slate-500">Includes requests patients raised for your facility. Confirm a donation once the donor has donated.</p>
        {reqs === null ? <Spinner /> : reqs.length === 0 ? <p className="text-sm text-slate-500 mt-4">No requests yet.</p> : (
          <div className="overflow-x-auto mt-4">
            <table className="w-full text-sm min-w-[900px]">
              <thead className="text-xs uppercase text-slate-500 bg-slate-50"><tr>
                <th className="text-left p-3">Req ID</th><th className="text-left p-3">Patient</th><th className="text-left p-3">Blood</th><th className="text-left p-3">Units</th>
                <th className="text-left p-3">Emergency</th><th className="text-left p-3">Status</th><th className="text-left p-3">Required</th><th className="text-left p-3">Accepted donors</th><th className="text-left p-3">Actions</th></tr></thead>
              <tbody>
                {reqs.map((r) => {
                  const live = !['COMPLETED', 'CANCELLED'].includes(r.status)
                  return (
                    <tr key={r.id} className="border-t border-slate-100 align-top">
                      <td className="p-3 font-bold">#{r.id}</td>
                      <td className="p-3">{r.patient_name || '—'}{r.notes && <p className="text-xs text-slate-400 max-w-[12rem]">{r.notes}</p>}</td>
                      <td className="p-3 font-black text-blood-600">{r.blood_group}</td>
                      <td className="p-3">{r.units_fulfilled}/{r.units_required}</td>
                      <td className="p-3"><UrgencyBadge level={r.emergency_level} /></td>
                      <td className="p-3"><StatusBadge status={r.status} /></td>
                      <td className="p-3 whitespace-nowrap">{r.required_date}<br /><span className="text-slate-400">{r.required_time}</span></td>
                      <td className="p-3">
                        {r.accepted_matches.length === 0 ? <span className="text-xs text-slate-400">{r.pending_matches} notified, none accepted</span> :
                          r.accepted_matches.map((m) => (
                            <div key={m.match_id} className="mb-2">
                              <p className="font-bold">{m.donor_name} <span className="text-blood-600">{m.donor_blood_group}</span></p>
                              <a href={`tel:${m.donor_phone}`} className="text-xs text-slate-500 flex items-center gap-1"><Phone className="w-3 h-3" />{m.donor_phone}</a>
                              {m.status === 'CONFIRMED' ? <span className="chip bg-emerald-50 text-emerald-700 mt-1">Confirmed</span>
                                : live && <button className="btn-primary btn-sm mt-1" onClick={() => setConfirm({ match: m, req: r, units: 1 })}>Confirm Donation</button>}
                            </div>
                          ))}
                      </td>
                      <td className="p-3 space-y-1">
                        <button className="block text-xs font-bold text-slate-700 hover:text-blood-600" onClick={() => setView(r.id)}>Matched donors</button>
                        {live && <button className="block text-xs font-bold text-slate-700 hover:text-blood-600" onClick={() => setStock({ req: r, units: r.units_required - r.units_fulfilled, blood_group: r.blood_group, component: 'WHOLE_BLOOD' })}>Issue from stock</button>}
                        {live && <button className="block text-xs font-bold text-red-600" disabled={busy === `c${r.id}`} onClick={() => act(`c${r.id}`, () => api.post(`/requests/${r.id}/cancel`), 'Cancel this request?')}>Cancel</button>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <MatchesModal requestId={view} onClose={() => setView(null)} />
      <Modal open={!!confirm} title="Confirm donation" onClose={() => setConfirm(null)}>
        {confirm && (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">Confirm that <strong>{confirm.match.donor_name}</strong> ({confirm.match.donor_blood_group}) donated for request #{confirm.req.id}. This updates the request status and the donor’s history.</p>
            <label className="label">Units transfused / collected
              <input type="number" min={1} max={4} className="input mt-1" value={confirm.units} onChange={(e) => setConfirm({ ...confirm, units: e.target.value })} /></label>
            <button className="btn-primary w-full" disabled={busy === 'confirm'} onClick={async () => {
              if (await act('confirm', () => api.post(`/matching/${confirm.match.match_id}/confirm`, { units: +confirm.units }))) setConfirm(null)
            }}>Confirm Donation</button>
          </div>
        )}
      </Modal>
      <Modal open={!!stock} title="Issue units from your stock" onClose={() => setStock(null)}>
        {stock && (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">Deducts red-cell units (whole blood or packed red cells) from your inventory and marks request #{stock.req.id} as completed.</p>
            <div className="grid grid-cols-3 gap-3">
              <label className="label">Component
                <select className="input mt-1" value={stock.component} onChange={(e) => setStock({ ...stock, component: e.target.value })}>
                  {RED_CELL_COMPONENTS.map((c) => <option key={c} value={c}>{componentLabel(c)}</option>)}</select></label>
              <label className="label">Blood group issued
                <select className="input mt-1" value={stock.blood_group} onChange={(e) => setStock({ ...stock, blood_group: e.target.value })}>
                  {canReceiveFrom(stock.req.blood_group).map((g) => <option key={g}>{g}</option>)}</select></label>
              <label className="label">Units
                <input type="number" min={1} max={20} className="input mt-1" value={stock.units} onChange={(e) => setStock({ ...stock, units: e.target.value })} /></label>
            </div>
            <button className="btn-primary w-full" disabled={busy === 'stock'} onClick={async () => {
              if (await act('stock', () => api.post(`/hospitals/${hid}/requests/${stock.req.id}/fulfill-from-stock`, { units: +stock.units, blood_group: stock.blood_group, component: stock.component }))) {
                setStock(null); window.dispatchEvent(new Event('bb:inventory'))
              }
            }}>Issue units</button>
          </div>
        )}
      </Modal>
    </div>
  )
}
