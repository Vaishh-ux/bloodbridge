import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="max-w-xl mx-auto px-4 py-20 text-center">
      <p className="text-6xl font-black text-blood-600">404</p>
      <p className="mt-3 font-bold text-navy-900">This page does not exist.</p>
      <Link to="/" className="btn-primary mt-6">Back to home</Link>
    </div>
  )
}
