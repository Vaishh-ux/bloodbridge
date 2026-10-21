import { createContext, useCallback, useContext, useState } from 'react'
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react'

const ToastCtx = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const dismiss = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), [])
  const push = useCallback((type, message, title) => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t.slice(-3), { id, type, message, title }])
    setTimeout(() => dismiss(id), type === 'error' ? 7000 : 5000)
  }, [dismiss])
  const api = {
    success: (m, t) => push('success', m, t),
    error: (m, t) => push('error', m, t),
    info: (m, t) => push('info', m, t),
  }
  const icon = { success: CheckCircle2, error: AlertTriangle, info: Info }
  const tone = {
    success: 'border-emerald-200 text-emerald-700',
    error: 'border-red-200 text-red-700',
    info: 'border-slate-200 text-slate-700',
  }
  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="fixed bottom-4 right-4 left-4 sm:left-auto z-[1000] flex flex-col gap-2 sm:w-96" aria-live="polite">
        {toasts.map((t) => {
          const Icon = icon[t.type]
          return (
            <div key={t.id} role="status" className={`bg-white border ${tone[t.type]} rounded-2xl shadow-xl p-4 flex gap-3 items-start`}>
              <Icon className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="flex-1 text-sm">
                {t.title && <p className="font-bold text-slate-900">{t.title}</p>}
                <p className="text-slate-600">{t.message}</p>
              </div>
              <button onClick={() => dismiss(t.id)} aria-label="Dismiss" className="text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
            </div>
          )
        })}
      </div>
    </ToastCtx.Provider>
  )
}

export const useToast = () => useContext(ToastCtx)
