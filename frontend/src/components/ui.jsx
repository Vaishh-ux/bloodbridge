import { AlertTriangle, Droplet, Loader2 } from 'lucide-react'
import { URGENCY_STYLE, STATUS_LABEL } from '../lib/blood'

export function Spinner({ label = 'Loading…', className = '' }) {
  return (
    <div className={`flex items-center justify-center gap-2 py-10 text-slate-500 text-sm ${className}`} role="status">
      <Loader2 className="w-5 h-5 animate-spin text-blood-600" /> {label}
    </div>
  )
}

export function Skeleton({ rows = 3 }) {
  return (
    <div className="space-y-3 animate-pulse" aria-hidden>
      {Array.from({ length: rows }).map((_, i) => <div key={i} className="h-20 bg-slate-100 rounded-2xl" />)}
    </div>
  )
}

export function Empty({ title, children, icon: Icon = Droplet }) {
  return (
    <div className="card p-10 text-center">
      <Icon className="w-10 h-10 mx-auto text-slate-300" />
      <p className="mt-3 font-bold text-slate-600">{title}</p>
      {children && <div className="mt-2 text-sm text-slate-500">{children}</div>}
    </div>
  )
}

export function ErrorBox({ message, onRetry }) {
  if (!message) return null
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 flex gap-3 items-start" role="alert">
      <AlertTriangle className="w-5 h-5 shrink-0" />
      <div className="flex-1">{message}</div>
      {onRetry && <button onClick={onRetry} className="font-bold underline">Retry</button>}
    </div>
  )
}

export function BloodBadge({ group, size = 'md' }) {
  const s = size === 'lg' ? 'w-14 h-14 text-lg' : size === 'sm' ? 'w-9 h-9 text-xs' : 'w-11 h-11 text-sm'
  return (
    <span className={`${s} shrink-0 rounded-2xl bg-blood-50 text-blood-600 font-black inline-flex items-center justify-center border border-blood-100`}>
      {group}
    </span>
  )
}

export const UrgencyBadge = ({ level }) => <span className={`chip ${URGENCY_STYLE[level] || ''}`}>{level}</span>

export function StatusBadge({ status }) {
  const tone = status === 'COMPLETED' ? 'bg-emerald-50 text-emerald-700'
    : status === 'CANCELLED' ? 'bg-slate-100 text-slate-500'
    : status === 'DONOR_ACCEPTED' || status === 'HOSPITAL_CONFIRMED' ? 'bg-sky-50 text-sky-700'
    : 'bg-amber-50 text-amber-700'
  return <span className={`chip ${tone}`}>{STATUS_LABEL[status] || status}</span>
}

export function PageHeader({ icon: Icon, title, subtitle, children }) {
  return (
    <div className="card p-6 mb-6 flex flex-col lg:flex-row lg:items-center gap-4 justify-between">
      <div>
        <h1 className="text-2xl font-black text-navy-900 flex items-center gap-2">
          {Icon && <Icon className="w-6 h-6 text-blood-600" />} {title}
        </h1>
        {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap gap-2 items-center">{children}</div>}
    </div>
  )
}

export function StatCard({ icon: Icon, label, value, tone = 'text-blood-600', hint }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
        {Icon && <Icon className={`w-5 h-5 ${tone}`} />}
      </div>
      <p className="mt-2 text-3xl font-black text-navy-900">{value ?? '—'}</p>
      {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
    </div>
  )
}

export function Field({ label, children, hint, required }) {
  return (
    <label className="block">
      <span className="label">{label}{required && <span className="text-blood-600"> *</span>}</span>
      {children}
      {hint && <span className="block text-xs text-slate-500 mt-1">{hint}</span>}
    </label>
  )
}

export function Modal({ open, title, onClose, children }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[900] bg-navy-950/60 flex items-center justify-center p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title}
           className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-slate-100">
          <h2 className="font-black text-lg text-navy-900">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-2xl leading-none" aria-label="Close">×</button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}
