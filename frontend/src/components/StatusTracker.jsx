import { Check } from 'lucide-react'
import { STATUS_STEPS } from '../lib/blood'

export default function StatusTracker({ status }) {
  if (status === 'CANCELLED') return <p className="text-sm font-bold text-slate-500">This request was cancelled.</p>
  const idx = STATUS_STEPS.findIndex((s) => s.key === status)
  return (
    <ol className="flex flex-wrap md:flex-nowrap gap-y-3 items-center" aria-label="Request progress">
      {STATUS_STEPS.map((s, i) => {
        const done = i < idx || status === 'COMPLETED'
        const current = i === idx && status !== 'COMPLETED'
        return (
          <li key={s.key} className="flex items-center flex-1 min-w-[6.5rem]" aria-current={current ? 'step' : undefined}>
            <span className={`w-7 h-7 shrink-0 rounded-full flex items-center justify-center text-xs font-black
              ${done ? 'bg-emerald-500 text-white' : current ? 'bg-blood-600 text-white ring-4 ring-blood-100' : 'bg-slate-100 text-slate-400'}`}>
              {done ? <Check className="w-4 h-4" /> : i + 1}
            </span>
            <span className={`ml-2 text-[11px] font-bold ${current ? 'text-blood-600' : done ? 'text-slate-700' : 'text-slate-400'}`}>{s.label}</span>
            {i < STATUS_STEPS.length - 1 && <span className={`hidden md:block flex-1 h-0.5 mx-2 ${done ? 'bg-emerald-400' : 'bg-slate-100'}`} />}
          </li>
        )
      })}
    </ol>
  )
}
