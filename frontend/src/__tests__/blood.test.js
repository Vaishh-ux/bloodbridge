import { describe, expect, it } from 'vitest'
import { BLOOD_GROUPS, canDonateTo, canReceiveFrom, isCompatible } from '../lib/blood'
import { errorMessage } from '../lib/api'
import { validateRegistration } from '../lib/validation'

describe('blood compatibility (mirrors backend)', () => {
  it('O- is universal red-cell donor, AB+ universal recipient', () => {
    BLOOD_GROUPS.forEach((g) => expect(isCompatible(g, 'O-')).toBe(true))
    BLOOD_GROUPS.forEach((g) => expect(isCompatible('AB+', g)).toBe(true))
  })
  it('Rh-negative recipients never receive Rh-positive', () => {
    ;['O-', 'A-', 'B-', 'AB-'].forEach((r) => canReceiveFrom(r).forEach((d) => expect(d.endsWith('-')).toBe(true)))
  })
  it('donate-to table', () => {
    expect(canDonateTo('O+').sort()).toEqual(['A+', 'AB+', 'B+', 'O+'])
    expect(canDonateTo('AB+')).toEqual(['AB+'])
  })
})

describe('errorMessage', () => {
  it('uses API detail string', () => {
    expect(errorMessage({ response: { status: 400, data: { detail: 'Nope' } } })).toBe('Nope')
  })
  it('explains unreachable server', () => {
    expect(errorMessage({ message: 'Network Error' })).toMatch(/Cannot reach/)
  })
  it('explains missing backend configuration', () => {
    expect(errorMessage({ isConfigError: true })).toMatch(/VITE_API_URL/)
  })
})

describe('registration validation', () => {
  const base = { role: 'DONOR', name: 'Asha R', email: 'a@example.com', phone: '+91 9876543210', password: 'Secret123', confirm: 'Secret123',
    city: 'Pune', state: 'Maharashtra', blood_group: 'O+', address: '', loc: null, meets_basic_criteria: true }
  it('accepts a valid donor', () => expect(validateRegistration(base)).toEqual({}))
  it('requires matching passwords and blood group', () => {
    const e = validateRegistration({ ...base, confirm: 'x', blood_group: '' })
    expect(e.confirm).toBeTruthy(); expect(e.blood_group).toBeTruthy()
  })
  it('requires a hospital address and location', () => {
    const e = validateRegistration({ ...base, role: 'HOSPITAL' })
    expect(e.address).toBeTruthy(); expect(e.loc).toBeTruthy()
  })
})

describe('static-host misconfiguration', () => {
  it('treats an HTML error page from /api as "server not connected"', () => {
    const e = { response: { status: 405, data: '<!DOCTYPE html><html><body>Method Not Allowed</body></html>' } }
    expect(errorMessage(e)).toMatch(/server is not connected/)
  })
})
