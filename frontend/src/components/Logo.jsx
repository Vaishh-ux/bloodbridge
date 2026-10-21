import { Droplet } from 'lucide-react'

export default function Logo({ dark = false }) {
  return (
    <span className="flex items-center gap-2 sm:gap-3">
      <span className="w-9 h-9 sm:w-11 sm:h-11 shrink-0 rounded-xl bg-blood-600 shadow-lg shadow-blood-600/30 flex items-center justify-center">
        <Droplet className="w-4 h-4 sm:w-5 sm:h-5 text-white fill-white" />
      </span>
      {/* Very narrow phones show only the icon so the header buttons fit. */}
      <span className="leading-tight max-[379px]:hidden">
        <span className={`block whitespace-nowrap font-black text-base sm:text-lg tracking-tight ${dark ? 'text-white' : 'text-navy-900'}`}>
          BLOOD<span className="text-blood-600">BRIDGE</span>
        </span>
        <span className={`hidden sm:block whitespace-nowrap text-[10px] font-semibold uppercase tracking-wider ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          Real-Time Donor Match
        </span>
      </span>
    </span>
  )
}
