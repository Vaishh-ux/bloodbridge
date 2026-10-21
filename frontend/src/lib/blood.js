export const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
export const URGENCY = ['Critical', 'High', 'Medium', 'Normal']

// recipient -> donor groups whose red cells are compatible (mirrors backend matching_service)
export const COMPATIBILITY = {
  'O-': ['O-'],
  'O+': ['O-', 'O+'],
  'A-': ['O-', 'A-'],
  'A+': ['O-', 'O+', 'A-', 'A+'],
  'B-': ['O-', 'B-'],
  'B+': ['O-', 'O+', 'B-', 'B+'],
  'AB-': ['O-', 'A-', 'B-', 'AB-'],
  'AB+': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'],
}

export const canReceiveFrom = (recipient) => COMPATIBILITY[recipient] || []
export const canDonateTo = (donor) => BLOOD_GROUPS.filter((r) => COMPATIBILITY[r].includes(donor))
export const isCompatible = (recipient, donor) => canReceiveFrom(recipient).includes(donor)

export const STATUS_STEPS = [
  { key: 'REQUESTED', label: 'Requested' },
  { key: 'SEARCHING', label: 'Searching' },
  { key: 'DONOR_FOUND', label: 'Donor Found' },
  { key: 'DONOR_ACCEPTED', label: 'Donor Accepted' },
  { key: 'HOSPITAL_CONFIRMED', label: 'Hospital Confirmed' },
  { key: 'COMPLETED', label: 'Completed' },
]

export const STATUS_LABEL = {
  REQUESTED: 'Requested', SEARCHING: 'Searching for donors', DONOR_FOUND: 'Donors notified',
  DONOR_ACCEPTED: 'Donor accepted', HOSPITAL_CONFIRMED: 'Hospital confirmed', COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
}

export const URGENCY_STYLE = {
  Critical: 'bg-red-600 text-white',
  High: 'bg-orange-100 text-orange-700 border border-orange-200',
  Medium: 'bg-amber-50 text-amber-700 border border-amber-200',
  Normal: 'bg-slate-100 text-slate-600 border border-slate-200',
}

export const DASHBOARD_PATH = {
  DONOR: '/donor-dashboard', PATIENT: '/patient-dashboard', HOSPITAL: '/hospital-dashboard', ADMIN: '/admin-dashboard',
}

export function timeAgo(iso) {
  if (!iso) return ''
  const t = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z').getTime()
  const s = Math.max(0, Math.round((Date.now() - t) / 1000))
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}

export const todayISO = () => {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

export const COMPONENTS = [
  { key: 'WHOLE_BLOOD', label: 'Whole Blood', short: 'WB' },
  { key: 'PRBC', label: 'Packed Red Cells', short: 'PRBC' },
  { key: 'PLATELETS', label: 'Platelets', short: 'PLT' },
  { key: 'PLASMA', label: 'Plasma', short: 'FFP' },
]
export const RED_CELL_COMPONENTS = ['WHOLE_BLOOD', 'PRBC']
export const componentLabel = (k) => COMPONENTS.find((c) => c.key === k)?.label || k
