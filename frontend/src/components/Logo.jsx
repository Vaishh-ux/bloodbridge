import { Droplet } from 'lucide-react'

export default function Logo({ dark = false }) {
  return (
    <span className="flex items-center gap-3">
      <span className="w-11 h-11 rounded-xl bg-blood-600 shadow-lg shadow-blood-600/30 flex items-center justify-center">
        <Droplet className="w-5 h-5 text-white fill-white" />
      </span>
      <span className="leading-tight">
        <span className={`block whitespace-nowrap font-black text-lg tracking-tight ${dark ? 'text-white' : 'text-navy-900'}`}>
          BLOOD<span className="text-blood-600">BRIDGE</span>
        </span>
        <span className={`block whitespace-nowrap text-[10px] font-semibold uppercase tracking-wider ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          Real-Time Donor Match
        </span>
      </span>
    </span>
  )
}
