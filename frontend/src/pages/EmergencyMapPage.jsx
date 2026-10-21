import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Map as MapIcon } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { useRealtimeEvent } from '../context/RealtimeContext'
import { EmergencyMap } from '../components/MapView'
import { ErrorBox, PageHeader } from '../components/ui'

export default function EmergencyMapPage() {
  const [requests, setRequests] = useState([])
  const [facilities, setFacilities] = useState([])
  const [err, setErr] = useState('')
  const nav = useNavigate()
  const load = useCallback(async () => {
    try {
      const [r, h] = await Promise.all([api.get('/requests'), api.get('/hospitals')])
      setRequests(r.data); setFacilities(h.data); setErr('')
    } catch (e) { setErr(errorMessage(e)) }
  }, [])
  useEffect(() => { load() }, [load])
  useRealtimeEvent(load, ['REQUEST_NEW', 'REQUEST_UPDATED'])

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <PageHeader icon={MapIcon} title="Live Emergency Map"
                  subtitle={`${requests.length} active request(s) · ${facilities.length} registered facilit${facilities.length === 1 ? 'y' : 'ies'}`}>
        <span className="flex flex-wrap gap-3 text-xs font-bold text-slate-600">
          <span className="flex items-center gap-1"><i className="w-3 h-3 rounded-full bg-red-600 inline-block" />Critical</span>
          <span className="flex items-center gap-1"><i className="w-3 h-3 rounded-full bg-orange-600 inline-block" />High</span>
          <span className="flex items-center gap-1"><i className="w-3 h-3 rounded-full bg-amber-600 inline-block" />Medium</span>
          <span className="flex items-center gap-1"><i className="w-3 h-3 rounded-full bg-slate-500 inline-block" />Normal</span>
          <span className="flex items-center gap-1"><i className="w-3 h-3 rounded-full bg-navy-900 inline-block" />Hospital</span>
          <span className="flex items-center gap-1"><i className="w-3 h-3 rounded-full bg-blue-600 inline-block" />Blood bank</span>
        </span>
      </PageHeader>
      <ErrorBox message={err} onRetry={load} />
      <EmergencyMap requests={requests} facilities={facilities} height={600} onRespond={() => nav('/requests')} />
      <p className="text-xs text-slate-500 mt-3">Request circles show an approximate area (about 1 km) to protect patient privacy. Facility pins show registered public addresses.</p>
    </div>
  )
}
