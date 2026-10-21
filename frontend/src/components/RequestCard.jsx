import { Building2, CalendarClock, MapPin, ShieldCheck } from 'lucide-react'
import { BloodBadge, StatusBadge, UrgencyBadge } from './ui'
import { timeAgo } from '../lib/blood'

export default function RequestCard({ req, children, distance }) {
  const critical = req.emergency_level === 'Critical'
  return (
    <article className={`card p-5 flex flex-col sm:flex-row gap-4 ${critical ? 'border-l-4 border-l-red-600' : ''}`}>
      <BloodBadge group={req.blood_group} size="lg" />
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <UrgencyBadge level={req.emergency_level} />
          <StatusBadge status={req.status} />
          <span className="text-xs text-slate-400">#{req.id} · {timeAgo(req.created_at)}</span>
        </div>
        <p className="mt-2 font-black text-navy-900">
          {req.units_required} unit{req.units_required > 1 ? 's' : ''} of {req.blood_group} needed
        </p>
        <div className="mt-1 text-sm text-slate-600 flex flex-wrap gap-x-4 gap-y-1">
          <span className="flex items-center gap-1"><Building2 className="w-4 h-4 text-slate-400" />{req.hospital_name}
            {req.is_verified_facility && <ShieldCheck className="w-4 h-4 text-emerald-500" title="Verified facility" />}</span>
          <span className="flex items-center gap-1"><MapPin className="w-4 h-4 text-slate-400" />{req.city}, {req.state}
            {distance != null && <strong className="ml-1 text-slate-700">· {distance} km</strong>}</span>
          <span className="flex items-center gap-1"><CalendarClock className="w-4 h-4 text-slate-400" />Needed {req.required_date} {req.required_time}</span>
        </div>
      </div>
      {children && <div className="flex sm:flex-col gap-2 sm:items-end justify-center">{children}</div>}
    </article>
  )
}
