import { useCallback, useEffect, useState } from 'react'
import { Bell } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { timeAgo } from '../lib/blood'
import { useRealtime, useRealtimeEvent } from '../context/RealtimeContext'
import { Empty, ErrorBox, PageHeader, Skeleton } from '../components/ui'

export default function Notifications() {
  const { setUnread } = useRealtime()
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState('')
  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/notifications', { params: { limit: 200 } })
      setRows(data.notifications); setUnread(data.unread_count); setErr('')
    } catch (e) { setErr(errorMessage(e)) }
  }, [setUnread])
  useEffect(() => { load() }, [load])
  useRealtimeEvent(load, ['NOTIFICATION_NEW'])

  const readAll = async () => { await api.put('/notifications/read-all'); load() }
  const readOne = async (n) => { if (!n.is_read) { await api.put(`/notifications/${n.id}/read`); load() } }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <PageHeader icon={Bell} title="Notifications Center" subtitle="View real-time alerts for requests and match updates">
        <button className="btn-ghost btn-sm" onClick={readAll}>Mark all read</button>
      </PageHeader>
      <ErrorBox message={err} onRetry={load} />
      {rows === null ? <Skeleton /> : rows.length === 0 ? <Empty title="No notifications available." icon={Bell} /> : (
        <ul className="card divide-y divide-slate-100">
          {rows.map((n) => (
            <li key={n.id}>
              <button onClick={() => readOne(n)} className={`w-full text-left p-5 hover:bg-slate-50 ${n.is_read ? '' : 'bg-blood-50/40'}`}>
                <p className="font-bold text-slate-800 flex items-center gap-2">{!n.is_read && <span className="w-2 h-2 rounded-full bg-blood-600" />}{n.title}</p>
                <p className="text-sm text-slate-600 mt-1">{n.message}</p>
                <p className="text-xs text-slate-400 mt-1">{timeAgo(n.created_at)}{n.request_id ? ` · request #${n.request_id}` : ''}</p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
