import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function CitizenDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] hero-grid text-white p-8">
      <div className="flex justify-between items-start mb-10">
        <div>
          <p className="font-mono text-green-500 text-xs tracking-widest mb-2 opacity-70">
            CITIZEN // SESSION_ACTIVE
          </p>
          <h1 className="font-mono font-bold text-3xl">Citizen Portal</h1>
          <p className="font-mono text-gray-500 text-xs mt-2">USER_ID: {user?.id}</p>
        </div>
        <button
          onClick={handleLogout}
          className="font-mono text-red-400 text-xs tracking-widest border border-red-500/50 px-4 py-2 hover:bg-red-500/10 transition-all"
        >
          LOGOUT
        </button>
      </div>

      <div className="border border-gray-800 bg-surface-panel p-8 max-w-2xl">
        <p className="font-mono text-gray-400 text-sm">
          Nearest shelter lookup and incident reporting will appear here once your
          zone is linked to your account.
        </p>
      </div>
    </div>
  )
}
