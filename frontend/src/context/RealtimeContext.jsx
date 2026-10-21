import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import api, { tokenStore, wsUrl } from '../lib/api'
import { useAuth } from './AuthContext'
import { useToast } from './ToastContext'

const RealtimeCtx = createContext(null)

/** Keeps one authenticated WebSocket open while logged in and fans events out to subscribers. */
export function RealtimeProvider({ children }) {
  const { user } = useAuth()
  const toast = useToast()
  const [unread, setUnread] = useState(0)
  const [connected, setConnected] = useState(false)
  const listeners = useRef(new Set())

  const refreshUnread = useCallback(async () => {
    if (!tokenStore.get()) return setUnread(0)
    try {
      const { data } = await api.get('/notifications', { params: { limit: 1 } })
      setUnread(data.unread_count)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    if (!user) { setUnread(0); return undefined }
    refreshUnread()
    let ws
    let closed = false
    let retry = 0
    let timer
    let ping

    const open = () => {
      const token = tokenStore.get()
      if (!token || closed) return
      try { ws = new WebSocket(wsUrl(token)) } catch { return }
      ws.onopen = () => {
        retry = 0
        setConnected(true)
        ping = setInterval(() => ws.readyState === 1 && ws.send('ping'), 25000)
      }
      ws.onmessage = (e) => {
        let msg
        try { msg = JSON.parse(e.data) } catch { return }
        if (msg.event === 'NOTIFICATION_NEW') {
          setUnread((n) => n + 1)
          // The requester already sees an on-screen confirmation for their own broadcast.
          if (msg.data.type !== 'REQUEST_BROADCAST') toast.info(msg.data.message, msg.data.title)
        }
        listeners.current.forEach((fn) => fn(msg))
      }
      ws.onclose = (e) => {
        setConnected(false)
        clearInterval(ping)
        if (closed || e.code === 4401) return
        retry = Math.min(retry + 1, 6)
        timer = setTimeout(open, 1000 * 2 ** retry)
      }
    }
    open()
    return () => {
      closed = true
      clearTimeout(timer)
      clearInterval(ping)
      ws?.close()
    }
  }, [user, refreshUnread]) // eslint-disable-line react-hooks/exhaustive-deps

  const subscribe = useCallback((fn) => {
    listeners.current.add(fn)
    return () => listeners.current.delete(fn)
  }, [])

  return (
    <RealtimeCtx.Provider value={{ unread, setUnread, refreshUnread, connected, subscribe }}>
      {children}
    </RealtimeCtx.Provider>
  )
}

export const useRealtime = () => useContext(RealtimeCtx)

/** Run `handler(msg)` for every real-time event (optionally filtered by event names). */
export function useRealtimeEvent(handler, events) {
  const { subscribe } = useRealtime()
  const ref = useRef(handler)
  ref.current = handler
  const key = events ? events.join(',') : ''
  useEffect(() => subscribe((msg) => {
    if (!key || key.split(',').includes(msg.event)) ref.current(msg)
  }), [subscribe, key])
}
