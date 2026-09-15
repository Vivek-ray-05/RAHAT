import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// Deliberately short per role -- each role only sees the handful of
// pages relevant to their job during an actual flood, not the whole
// product surface. See the plan this was built from: a coordinator
// shouldn't have to hunt through a citizen's or an NDRF team's pages.
const NAV_BY_ROLE = {
  central_coordinator: [
    { label: 'DASHBOARD', path: '/dashboard' },
    { label: 'ROUTE_PLAN', path: '/dashboard/route-plan' },
    { label: 'SIMULATION', path: '/dashboard/simulation' },
    { label: 'ZONAL_ANALYSIS', path: '/dashboard/zonal-analysis' },
    { label: 'SHELTER_STATUS', path: '/dashboard/shelter-status' },
  ],
  zone_admin: [
    { label: 'ROUTE_PLANNING', path: '/dashboard/zone' },
    { label: 'SHELTER_MANAGEMENT', path: '/dashboard/zone/shelter-management' },
    { label: 'ZONE_STATUS', path: '/dashboard/zone/status' },
  ],
  citizen: [
    { label: 'EMERGENCY_SOS', path: '/dashboard/citizen' },
    { label: 'REPORT_FILING', path: '/dashboard/citizen/report' },
    { label: 'DIRECTIONS', path: '/dashboard/citizen/directions' },
  ],
  ndrf: [
    { label: 'RESPONSE', path: '/dashboard/rescue' },
  ],
}

export default function Sidebar() {
  const { user } = useAuth()
  const location = useLocation()
  const items = NAV_BY_ROLE[user?.role] || []

  return (
    <aside className="w-56 border-r border-gray-800 bg-surface-panel flex flex-col p-4 shrink-0">
      <nav className="flex flex-col gap-1">
        {items.map((item) => {
          const active = location.pathname === item.path
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`font-mono text-xs tracking-widest px-3 py-2 border transition-all ${
                active
                  ? 'border-green-500 text-green-400 bg-green-500/10'
                  : 'border-transparent text-gray-500 hover:text-gray-300 hover:border-gray-700'
              }`}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
