import axios from 'axios'

/**
 * API base URL.
 *  - Local dev: leave VITE_API_URL unset -> "/api" (proxied by Vite to http://localhost:8000).
 *  - Production (e.g. Netlify): set VITE_API_URL=https://your-backend.onrender.com/api at build time.
 */
export const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '')

export function wsUrl(token) {
  let base
  if (/^https?:\/\//.test(API_BASE)) {
    const u = new URL(API_BASE)
    base = `${u.protocol === 'https:' ? 'wss:' : 'ws:'}//${u.host}`
  } else {
    base = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
  }
  return `${base}/ws?token=${encodeURIComponent(token)}`
}

const TOKEN_KEY = 'bb_token'
export const tokenStore = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  set: (t) => { try { localStorage.setItem(TOKEN_KEY, t) } catch { /* storage unavailable */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY) } catch { /* storage unavailable */ } },
}

const api = axios.create({ baseURL: API_BASE, timeout: 20000 })

api.interceptors.request.use((config) => {
  const t = tokenStore.get()
  if (t) config.headers.Authorization = `Bearer ${t}`
  return config
})

api.interceptors.response.use(
  (res) => {
    // A static host (e.g. Netlify SPA fallback) answers unknown /api paths with index.html.
    const ct = res.headers?.['content-type'] || ''
    if (ct.includes('text/html')) {
      const err = new Error('BACKEND_NOT_CONFIGURED')
      err.isConfigError = true
      return Promise.reject(err)
    }
    return res
  },
  (error) => {
    if (error.response?.status === 401 && tokenStore.get()) {
      tokenStore.clear()
      window.dispatchEvent(new Event('bb:logout'))
    }
    return Promise.reject(error)
  },
)

/** Human-readable message for any API error. */
export function errorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!error) return fallback
  const body = error.response?.data
  const htmlBody = typeof body === 'string' && /<(!doctype|html)/i.test(body)
  if (error.isConfigError || htmlBody) {
    // A static host answered instead of the FastAPI backend (wrong/missing VITE_API_URL).
    return 'The Blood Bridge server is not connected. Set VITE_API_URL to your backend URL and redeploy.'
  }
  if (error.code === 'ECONNABORTED') return 'The server took too long to respond. Please try again.'
  if (!error.response) {
    return 'Cannot reach the Blood Bridge server. Check your connection or that the backend is running.'
  }
  const d = error.response.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg?.replace(/^Value error, /, '')).join('; ')
  if (error.response.status === 429) return 'Too many attempts. Please wait a minute.'
  return fallback
}

export default api
