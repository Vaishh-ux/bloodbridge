import { useEffect, useState } from 'react'
import L from 'leaflet'
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { Crosshair, Search, Loader2 } from 'lucide-react'
import { currentPosition, directionsUrl, geocode } from '../lib/geo'

const INDIA = [22.5, 79]
const TILE = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

const pin = (bg, glyph) => L.divIcon({
  className: 'bb-pin',
  html: `<div style="background:${bg};width:30px;height:30px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;box-shadow:0 4px 10px rgba(0,0,0,.25);border:2px solid #fff"><span style="transform:rotate(45deg);color:#fff;font-size:13px;font-weight:800">${glyph}</span></div>`,
  iconSize: [30, 30], iconAnchor: [15, 30], popupAnchor: [0, -28],
})
export const ICONS = {
  hospital: pin('#0f172a', 'H'),
  bank: pin('#2563eb', 'B'),
  me: pin('#16a34a', '•'),
  point: pin('#e11d48', '+'),
}
const URGENCY_COLOR = { Critical: '#dc2626', High: '#ea580c', Medium: '#d97706', Normal: '#64748b' }

function FitBounds({ points }) {
  const map = useMap()
  const key = points.map((p) => p.join(',')).join('|')
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 12)
    else if (points.length > 1) map.fitBounds(points, { padding: [40, 40], maxZoom: 13 })
  }, [key]) // eslint-disable-line react-hooks/exhaustive-deps
  return null
}

/** Requests are drawn as ~1 km circles around an approximate point – never an exact location. */
export function EmergencyMap({ requests = [], facilities = [], me, height = 480, onRespond }) {
  const pts = [
    ...requests.map((r) => [r.approx_latitude, r.approx_longitude]),
    ...facilities.filter((h) => h.latitude != null).map((h) => [h.latitude, h.longitude]),
    ...(me ? [[me.lat, me.lng]] : []),
  ].filter(([a, b]) => a != null && b != null)
  return (
    <div className="rounded-3xl overflow-hidden border border-slate-100 shadow-sm" style={{ height }}>
      <MapContainer center={INDIA} zoom={5} style={{ height: '100%', width: '100%' }} scrollWheelZoom={false}>
        <TileLayer url={TILE} attribution={ATTR} />
        <FitBounds points={pts} />
        {requests.map((r) => (
          <Circle key={`r${r.id}`} center={[r.approx_latitude, r.approx_longitude]} radius={1000}
                  pathOptions={{ color: URGENCY_COLOR[r.emergency_level], fillOpacity: 0.35, weight: 2 }}>
            <Popup>
              <strong>{r.blood_group} · {r.units_required} unit(s)</strong><br />
              {r.emergency_level} · {r.hospital_name}<br />
              <span style={{ color: '#64748b' }}>Approximate area (≈1 km)</span>
              {onRespond && <><br /><button className="mt-1 font-bold text-blood-600" onClick={() => onRespond(r)}>View request →</button></>}
            </Popup>
          </Circle>
        ))}
        {facilities.filter((h) => h.latitude != null).map((h) => (
          <Marker key={`h${h.id}`} position={[h.latitude, h.longitude]} icon={h.facility_type === 'BLOOD_BANK' ? ICONS.bank : ICONS.hospital}>
            <Popup>
              <strong>{h.name}</strong>{h.verified ? ' ✓' : ''}<br />
              {h.address}, {h.city}<br />
              {h.phone && <a href={`tel:${h.phone}`}>{h.phone}</a>}<br />
              <a href={directionsUrl(h.latitude, h.longitude)} target="_blank" rel="noreferrer">Directions</a>
            </Popup>
          </Marker>
        ))}
        {me && <Marker position={[me.lat, me.lng]} icon={ICONS.me}><Popup>You are here</Popup></Marker>}
      </MapContainer>
    </div>
  )
}

function ClickToSet({ onPick }) {
  useMapEvents({ click: (e) => onPick({ lat: +e.latlng.lat.toFixed(5), lng: +e.latlng.lng.toFixed(5) }) })
  return null
}

/** Lets a user set coordinates by GPS, address search, or clicking the map. */
export function LocationPicker({ value, onChange, addressHint = '', label = 'Location' }) {
  const [busy, setBusy] = useState(null)
  const [err, setErr] = useState('')
  const [q, setQ] = useState('')
  const has = value?.lat != null && value?.lng != null

  const run = async (kind) => {
    setErr(''); setBusy(kind)
    try {
      const p = kind === 'gps' ? await currentPosition() : await geocode(q || addressHint)
      onChange({ lat: p.lat, lng: p.lng })
    } catch (e) { setErr(e.message) } finally { setBusy(null) }
  }

  return (
    <div className="rounded-2xl border border-slate-200 p-4 bg-slate-50/50">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <span className="label mb-0">{label}</span>
        <span className={`text-xs font-bold ${has ? 'text-emerald-600' : 'text-slate-500'}`}>
          {has ? `Set: ${value.lat}, ${value.lng}` : 'Not set'}
        </span>
      </div>
      <div className="flex flex-col sm:flex-row gap-2">
        <input className="input" placeholder={addressHint ? `Search: ${addressHint}` : 'Search address, area or PIN code'}
               value={q} onChange={(e) => setQ(e.target.value)}
               onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); run('geo') } }} />
        <button type="button" className="btn-ghost btn-sm whitespace-nowrap" onClick={() => run('geo')} disabled={!!busy || !(q || addressHint)}>
          {busy === 'geo' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Locate
        </button>
        <button type="button" className="btn-ghost btn-sm whitespace-nowrap" onClick={() => run('gps')} disabled={!!busy}>
          {busy === 'gps' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Crosshair className="w-4 h-4" />} Use my location
        </button>
      </div>
      {err && <p className="text-xs text-red-600 mt-2">{err}</p>}
      <div className="mt-3 rounded-xl overflow-hidden border border-slate-200" style={{ height: 220 }}>
        <MapContainer center={has ? [value.lat, value.lng] : INDIA} zoom={has ? 14 : 4} style={{ height: '100%' }}>
          <TileLayer url={TILE} attribution={ATTR} />
          <ClickToSet onPick={onChange} />
          {has && <><Marker position={[value.lat, value.lng]} icon={ICONS.point} /><FitBounds points={[[value.lat, value.lng]]} /></>}
        </MapContainer>
      </div>
      <p className="text-[11px] text-slate-500 mt-2">Tip: click the map to fine-tune the point. Address search uses OpenStreetMap Nominatim.</p>
    </div>
  )
}
