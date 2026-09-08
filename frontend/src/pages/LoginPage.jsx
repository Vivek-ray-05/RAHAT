import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const ROLES = [
  { value: 'central_coordinator', label: 'CENTRAL_COORDINATOR', mode: 'password' },
  { value: 'zone_admin', label: 'ZONE_ADMIN', mode: 'password' },
  { value: 'ndrf', label: 'NDRF', mode: 'otp' },
  { value: 'citizen', label: 'CITIZEN', mode: 'otp' },
]

const ROLE_HOME = {
  central_coordinator: '/dashboard',
  zone_admin: '/dashboard/zone',
  ndrf: '/dashboard/rescue',
  citizen: '/dashboard/citizen',
}

export default function LoginPage() {
  const [role, setRole] = useState('zone_admin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [devOtp, setDevOtp] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()
  const { loginWithPassword, requestOtp, verifyOtp } = useAuth()

  const selectedRole = ROLES.find((r) => r.value === role)

  async function handlePasswordSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await loginWithPassword(email, password, role)
      navigate(ROLE_HOME[data.role] || '/')
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleRequestOtp(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await requestOtp(phone)
      setOtpSent(true)
      setDevOtp(data.dev_otp || null)
    } catch (err) {
      setError(err.message || 'Could not send OTP')
    } finally {
      setLoading(false)
    }
  }

  async function handleVerifyOtp(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await verifyOtp(phone, code)
      navigate(ROLE_HOME[data.role] || '/')
    } catch (err) {
      setError(err.message || 'Invalid code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] hero-grid flex items-center justify-center p-8">
      <div className="w-full max-w-md">
        <p className="font-mono text-green-500 text-xs tracking-widest mb-6 opacity-70">
          AUTH_GATEWAY // SELECT_ROLE
        </p>

        <div className="grid grid-cols-2 gap-2 mb-8">
          {ROLES.map((r) => (
            <button
              key={r.value}
              type="button"
              onClick={() => {
                setRole(r.value)
                setError('')
                setOtpSent(false)
              }}
              className={`font-mono text-xs tracking-widest px-3 py-3 border transition-all ${
                role === r.value
                  ? 'border-green-500 text-green-400 bg-green-500/10'
                  : 'border-gray-700 text-gray-500 hover:border-gray-500'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>

        {selectedRole.mode === 'password' && (
          <form onSubmit={handlePasswordSubmit} className="flex flex-col gap-4">
            <input
              type="email"
              placeholder="EMAIL"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-sm px-4 py-3 outline-none placeholder:text-gray-600"
            />
            <input
              type="password"
              placeholder="PASSWORD"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-sm px-4 py-3 outline-none placeholder:text-gray-600"
            />
            <button
              type="submit"
              disabled={loading}
              className="font-mono text-green-400 text-sm tracking-widest border border-green-500 px-8 py-4 hover:bg-green-500/10 transition-all duration-200 disabled:opacity-40"
            >
              {loading ? 'AUTHENTICATING...' : 'AUTHENTICATE →'}
            </button>
          </form>
        )}

        {selectedRole.mode === 'otp' && !otpSent && (
          <form onSubmit={handleRequestOtp} className="flex flex-col gap-4">
            <input
              type="tel"
              placeholder="PHONE"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
              className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-sm px-4 py-3 outline-none placeholder:text-gray-600"
            />
            <button
              type="submit"
              disabled={loading}
              className="font-mono text-green-400 text-sm tracking-widest border border-green-500 px-8 py-4 hover:bg-green-500/10 transition-all duration-200 disabled:opacity-40"
            >
              {loading ? 'SENDING...' : 'SEND_CODE →'}
            </button>
          </form>
        )}

        {selectedRole.mode === 'otp' && otpSent && (
          <form onSubmit={handleVerifyOtp} className="flex flex-col gap-4">
            {devOtp && (
              <p className="font-mono text-xs text-gray-500 tracking-widest">
                DEV_MODE // CODE: <span className="text-green-400">{devOtp}</span>
              </p>
            )}
            <input
              type="text"
              placeholder="CODE"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
              className="bg-transparent border border-gray-700 focus:border-green-500 text-green-400 font-mono text-sm px-4 py-3 outline-none placeholder:text-gray-600"
            />
            <button
              type="submit"
              disabled={loading}
              className="font-mono text-green-400 text-sm tracking-widest border border-green-500 px-8 py-4 hover:bg-green-500/10 transition-all duration-200 disabled:opacity-40"
            >
              {loading ? 'VERIFYING...' : 'VERIFY →'}
            </button>
          </form>
        )}

        {error && (
          <p className="font-mono text-red-400 text-xs tracking-widest mt-4">{`ERROR: ${error}`}</p>
        )}
      </div>
    </div>
  )
}
