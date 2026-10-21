/** Browser geolocation, resolved as {lat, lng}. */
export function currentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('Location is not supported by this browser.'))
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: +p.coords.latitude.toFixed(5), lng: +p.coords.longitude.toFixed(5) }),
      (e) => reject(new Error(e.code === 1 ? 'Location permission was denied.' : 'Could not get your location.')),
      { enableHighAccuracy: true, timeout: 10000 },
    )
  })
}

/**
 * Address -> coordinates using OpenStreetMap Nominatim (free, ~1 request/second fair use).
 * https://operations.osmfoundation.org/policies/nominatim/
 */
export async function geocode(query) {
  const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(query)}`
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error('Address lookup failed. Try again or pick the point on the map.')
  const data = await res.json()
  if (!data.length) throw new Error('Address not found. Try adding the city/PIN code or pick it on the map.')
  return { lat: +(+data[0].lat).toFixed(5), lng: +(+data[0].lon).toFixed(5), label: data[0].display_name }
}

export const directionsUrl = (lat, lng) =>
  `https://www.openstreetmap.org/directions?route=%3B${lat}%2C${lng}#map=15/${lat}/${lng}`
export const mapUrl = (lat, lng) => `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=16/${lat}/${lng}`
