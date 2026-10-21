import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell } from 'lucide-react'
import api from '../lib/api'
import { timeAgo } from '../lib/blood'
import { useRealtime, useRealtimeEvent } from '../context/RealtimeContext'

export default function NotificationBell() {
  const { unread, setUnread } = useRealtime()
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState(null)
  const ref = useRef(null)

  const load = async () => {
    try {
      const { data } = await api.get('/notifications', { params: { limit: 8 } })
      setItems(data.notifications)
      setUnread(data.unread_count)
    } catch { setItems([]) }
  }

  useRealtimeEvent(() => { if (open) load() }, ['NOTIFICATION_NEW'])
  useEffect(() => { if (open) load() }, [open]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const close = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const markAll = async () => {
    await api.put('/notifications/read-all')
    setUnread(0)
    setItems((xs) => xs?.map((x) => ({ ...x, is_read: true })))
  }
  const markOne = async (n) => {
    if (n.is_read) return
    await api.put(`/notifications/${n.id}/read`)
    setUnread((u) => Math.max(0, u - 1))
    setItems((xs) => xs.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)))
  }

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} aria-label={`Notifications (${unread} unread)`}
              className="relative p-2 rounded-xl text-slate-600 hover:bg-slate-100">
        <Bell className="w-5 h-5" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-blood-600 text-white text-[10px] font-bold flex items-center justify-center">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] bg-white rounded-2xl shadow-2xl border border-slate-100 z-[800]">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
            <p className="font-black text-navy-900">Notifications</p>
            <button onClick={markAll} className="text-xs font-bold text-blood-600 hover:underline">Mark all read</button>
          </div>
          <div className="max-h-96 overflow-auto">
            {items === null && <p className="p-4 text-sm text-slate-500">Loading…</p>}
            {items?.length === 0 && <p className="p-6 text-sm text-slate-500 text-center">No notifications yet</p>}
            {items?.map((n) => (
              <button key={n.id} onClick={() => markOne(n)}
                      className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 ${n.is_read ? '' : 'bg-blood-50/50'}`}>
                <p className="text-sm font-bold text-slate-800 flex gap-2">
                  {!n.is_read && <span className="mt-1.5 w-2 h-2 rounded-full bg-blood-600 shrink-0" />}{n.title}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">{n.message}</p>
                <p className="text-[10px] text-slate-400 mt-1">{timeAgo(n.created_at)}</p>
              </button>
            ))}
          </div>
          <Link to="/notifications" onClick={() => setOpen(false)} className="block text-center text-xs font-bold text-slate-600 py-3 hover:bg-slate-50 rounded-b-2xl">
            View all notifications →
          </Link>
        </div>
      )}
    </div>
  )
}
