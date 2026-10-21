/** Client-side checks that mirror the backend's registration rules. */
export function validateRegistration(f) {
  const e = {}
  if (f.name.trim().length < 2) e.name = 'Enter your full name.'
  if (!/^\S+@\S+\.\S+$/.test(f.email.trim())) e.email = 'Enter a valid email address.'
  if (!/^\+?[0-9][0-9\s-]{6,18}$/.test(f.phone.trim())) e.phone = 'Enter a valid phone number.'
  if (f.password.length < 8 || !/[A-Za-z]/.test(f.password) || !/\d/.test(f.password)) e.password = 'At least 8 characters with a letter and a number.'
  if (f.password !== f.confirm) e.confirm = 'Passwords do not match.'
  if (f.city.trim().length < 2) e.city = 'City is required.'
  if (f.state.trim().length < 2) e.state = 'State is required.'
  if (f.role === 'DONOR' && !f.blood_group) e.blood_group = 'Blood group is required.'
  if (f.role === 'HOSPITAL' && f.address.trim().length < 5) e.address = 'Facility address is required.'
  if (f.role === 'HOSPITAL' && !f.loc) e.loc = 'Set the facility location so it appears on the map.'
  if (f.role === 'DONOR' && !f.meets_basic_criteria) e.meets_basic_criteria = 'Please confirm the basic screening questions (you can still register but will not be matched until you do).'
  return e
}
