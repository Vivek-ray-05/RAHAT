import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const ROLE_LABEL = {
  central_coordinator: 'CENTRAL_COORDINATOR',
  zone_admin: 'ZONE_ADMIN',
  citizen: 'CITIZEN',
  ndrf: 'NDRF',
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <header className="flex justify-between items-center border-b border-gray-800 bg-surface-panel px-6 py-3 shrink-0">
      <div>
        <p className="font-mono font-bold text-white text-sm tracking-widest">RAHAT</p>
        <p className="font-mono text-green-500 text-[10px] tracking-widest opacity-70">
          {ROLE_LABEL[user?.role] || user?.role} // SESSION_ACTIVE // USER_ID: {user?.id}
        </p>
      </div>
      <button
        onClick={handleLogout}
        className="font-mono text-red-400 text-xs tracking-widest border border-red-500/50 px-4 py-2 hover:bg-red-500/10 transition-all"
      >
        LOGOUT
      </button>
    </header>
  )
}
