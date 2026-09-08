import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const BOOT_TEXT = [
  "RAHAT_SYSTEM // v1.0.0",
  "HUMAN-IN-THE-LOOP EVACUATION PLATFORM",
  "LOADING RISK / VULNERABILITY / MOBILITY ENGINES...",
  "LOADING [████████████████] 100%",
  "BENGALURU_METRO // ZONES: 28 // ONLINE",
  "APPROVAL_GATE // ACTIVE",
  "AUTH_GATEWAY // STANDING_BY",
  ">> SYSTEM READY",
]

export default function LandingPage() {
  const [bootLines, setBootLines] = useState([])
  const [bootComplete, setBootComplete] = useState(false)

  useEffect(() => {
    let currentIndex = 0
    const intervalId = setInterval(() => {
      setBootLines((prev) => {
        if (currentIndex < BOOT_TEXT.length) {
          return [...prev, BOOT_TEXT[currentIndex]]
        }
        return prev
      })
      currentIndex++

      if (currentIndex > BOOT_TEXT.length) {
        clearInterval(intervalId)
        setTimeout(() => setBootComplete(true), 800)
      }
    }, 400)

    return () => clearInterval(intervalId)
  }, [])

  if (!bootComplete) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex flex-col justify-center items-center p-8">
        <div className="w-full max-w-2xl flex flex-col items-start space-y-2">
          {bootLines.map((line, idx) => (
            <div key={idx} className="text-green-400 font-mono text-sm tracking-wider">
              {line}
              {idx === bootLines.length - 1 && <span className="animate-pulse ml-2">█</span>}
            </div>
          ))}
          {bootLines.length === 0 && (
            <div className="text-green-400 font-mono text-sm tracking-wider">
              <span className="animate-pulse">█</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  return <HeroSection />
}

function HeroSection() {
  const [stats, setStats] = useState({ zones: 0, population: 0, engines: 0, connected: 0 })
  const navigate = useNavigate()

  useEffect(() => {
    // Real total population summed from RAHAT's 28 seeded Bengaluru zones (1,254,368)
    const targets = { zones: 28, population: 1254, engines: 4, connected: 28 }
    const keys = Object.keys(targets)
    const intervals = keys.map((key) => {
      const step = Math.max(1, Math.round(targets[key] / 40)) // ~40 ticks to finish regardless of target size
      return setInterval(() => {
        setStats((prev) => {
          if (prev[key] >= targets[key]) return prev
          return { ...prev, [key]: Math.min(targets[key], prev[key] + step) }
        })
      }, 40)
    })
    return () => intervals.forEach(clearInterval)
  }, [])

  return (
    <div className="min-h-screen bg-[#0a0a0a] hero-grid relative overflow-hidden">
      <div
        className="absolute top-0 left-0 w-96 h-96 rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(ellipse, rgba(0,255,136,0.06) 0%, transparent 70%)' }}
      />

      <div className="flex min-h-screen flex-col md:flex-row">
        <div className="w-full md:w-[55%] pl-8 md:pl-16 pr-8 py-16 flex flex-col justify-center">
          <p className="font-mono text-green-500 text-xs tracking-widest mb-6 opacity-70">
            SYSTEM_STATUS_ACTIVE // BENGALURU_METRO
          </p>

          <h1
            className="font-mono font-bold text-white leading-none mb-2"
            style={{ fontSize: 'clamp(64px,10vw,130px)', letterSpacing: '0.08em' }}
          >
            RAHAT
          </h1>

          <p className="font-mono text-green-400 text-xs tracking-widest uppercase mb-6">
            Human-in-the-loop disaster evacuation platform
          </p>

          <div className="w-full h-px bg-green-500 opacity-20 mb-6" />

          <p className="font-mono text-gray-400 text-sm leading-relaxed max-w-md mb-10">
            AI recommends. Humans approve. Real risk and vulnerability scoring, real
            road-network routing across 28 Bengaluru localities -- every evacuation
            recommendation waits for a zone admin's sign-off before it becomes real.
          </p>

          <div className="flex gap-8 flex-wrap">
            <div>
              <div className="font-mono font-bold text-green-400 text-3xl">{stats.zones}</div>
              <div className="font-mono text-gray-500 text-xs tracking-widest mt-1">ZONES_MONITORED</div>
            </div>
            <div>
              <div className="font-mono font-bold text-green-400 text-3xl">{(stats.population / 1000).toFixed(2)}M</div>
              <div className="font-mono text-gray-500 text-xs tracking-widest mt-1">POPULATION_MODELED</div>
            </div>
            <div>
              <div className="font-mono font-bold text-green-400 text-3xl">{stats.engines}</div>
              <div className="font-mono text-gray-500 text-xs tracking-widest mt-1">DECISION_ENGINES</div>
            </div>
            <div>
              <div className="font-mono font-bold text-green-400 text-3xl">{stats.connected}</div>
              <div className="font-mono text-gray-500 text-xs tracking-widest mt-1">ROAD_NETWORK_ZONES</div>
            </div>
          </div>

          <button
            onClick={() => navigate('/login')}
            className="font-mono text-green-400 text-sm tracking-widest border border-green-500 px-8 py-4 mt-10 hover:bg-green-500/10 transition-all duration-200 flex items-center gap-3 w-fit"
          >
            ENTER_SYSTEM
            <span>→</span>
          </button>
        </div>

        <div className="w-full md:w-[45%] h-[420px] md:h-screen flex items-center justify-center relative">
          <RadarDisplay />
        </div>
      </div>
    </div>
  )
}

// A representative subset of RAHAT's real 28 seeded Bengaluru zones,
// spread across the compass for the radar display.
const RADAR_ZONES = [
  { id: 'Z10', name: 'YELAHANKA', angle: 340, dist: 0.85 },
  { id: 'Z12', name: 'HEBBAL', angle: 355, dist: 0.6 },
  { id: 'Z06', name: 'WHITEFIELD', angle: 45, dist: 0.8 },
  { id: 'Z24', name: 'K.R.PURAM', angle: 25, dist: 0.55 },
  { id: 'Z03', name: 'INDIRANAGAR', angle: 10, dist: 0.35 },
  { id: 'Z04', name: 'KORAMANGALA', angle: 150, dist: 0.4 },
  { id: 'Z02', name: 'BELLANDUR', angle: 120, dist: 0.55, critical: true },
  { id: 'Z01', name: 'MARATHAHALLI', angle: 75, dist: 0.55 },
  { id: 'Z05', name: 'HSR LAYOUT', angle: 170, dist: 0.5 },
  { id: 'Z23', name: 'BTM LAYOUT', angle: 200, dist: 0.55 },
  { id: 'Z22', name: 'JP NAGAR', angle: 220, dist: 0.7 },
  { id: 'Z11', name: 'SARJAPUR RD', angle: 140, dist: 0.8 },
  { id: 'Z07', name: 'ELECTRONIC CITY', angle: 195, dist: 0.9 },
  { id: 'Z09', name: 'MALLESWARAM', angle: 280, dist: 0.55 },
]

function RadarDisplay() {
  const [angle, setAngle] = useState(0)
  const [visibleBlips, setVisibleBlips] = useState(new Set())
  const [tick, setTick] = useState(0)

  const CENTER = { x: 200, y: 200 }
  const RADIUS = 180

  const toXY = (angleDeg, dist) => {
    const rad = ((angleDeg - 90) * Math.PI) / 180
    return {
      x: CENTER.x + Math.cos(rad) * RADIUS * dist,
      y: CENTER.y + Math.sin(rad) * RADIUS * dist,
    }
  }

  useEffect(() => {
    const interval = setInterval(() => setAngle((prev) => (prev + 1) % 360), 8)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const t = setInterval(() => setTick((p) => p + 1), 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    RADAR_ZONES.forEach((blip) => {
      const diff = (angle - blip.angle + 360) % 360
      if (diff < 3) {
        setVisibleBlips((prev) => new Set([...prev, blip.id]))
      }
    })
  }, [angle])

  const sweepRad = ((angle - 90) * Math.PI) / 180
  const sweepX = CENTER.x + Math.cos(sweepRad) * RADIUS
  const sweepY = CENTER.y + Math.sin(sweepRad) * RADIUS

  const trailPath = () => {
    const steps = 60
    let d = `M ${CENTER.x} ${CENTER.y}`
    for (let i = steps; i >= 0; i--) {
      const a = (((angle - i - 90 + 360) % 360) * Math.PI) / 180
      const x = CENTER.x + Math.cos(a) * RADIUS
      const y = CENTER.y + Math.sin(a) * RADIUS
      d += ` L ${x} ${y}`
    }
    return d
  }

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <div className="absolute right-4 top-1/2 -translate-y-1/2 flex flex-col gap-3 z-10">
        {[
          `LIVE_TICK: ${String(tick).padStart(4, '0')}`,
          'ENGINES: 4/4',
          'DB: CONNECTED',
          'FLOOD_MODEL: ON',
          `SWEEP: ${angle}°`,
        ].map((s, i) => (
          <div key={i} className="font-mono text-green-500 text-xs tracking-widest opacity-60">
            {s}
          </div>
        ))}
      </div>

      <svg
        viewBox="0 0 400 400"
        width="420"
        height="420"
        style={{ filter: 'drop-shadow(0 0 30px rgba(0,255,136,0.2))' }}
      >
        <circle cx={CENTER.x} cy={CENTER.y} r={RADIUS} fill="rgba(0,255,136,0.02)" stroke="rgba(0,255,136,0.15)" strokeWidth="1" />

        {[0.25, 0.5, 0.75, 1].map((r, i) => (
          <circle key={i} cx={CENTER.x} cy={CENTER.y} r={RADIUS * r} fill="none" stroke="rgba(0,255,136,0.1)" strokeWidth="1" />
        ))}

        {[0.25, 0.5, 0.75].map((r, i) => (
          <text key={i} x={CENTER.x + 4} y={CENTER.y - RADIUS * r + 10} fill="rgba(0,255,136,0.3)" fontSize="7" fontFamily="monospace">
            {Math.round(r * 15)}KM
          </text>
        ))}

        <line x1={CENTER.x} y1={CENTER.y - RADIUS} x2={CENTER.x} y2={CENTER.y + RADIUS} stroke="rgba(0,255,136,0.08)" strokeWidth="1" />
        <line x1={CENTER.x - RADIUS} y1={CENTER.y} x2={CENTER.x + RADIUS} y2={CENTER.y} stroke="rgba(0,255,136,0.08)" strokeWidth="1" />

        <path d={trailPath()} fill="rgba(0,255,136,0.06)" stroke="none" />
        <line x1={CENTER.x} y1={CENTER.y} x2={sweepX} y2={sweepY} stroke="rgba(0,255,136,0.9)" strokeWidth="1.5" />
        <circle cx={CENTER.x} cy={CENTER.y} r="3" fill="#00ff88" />

        {RADAR_ZONES.map((blip) => {
          const pos = toXY(blip.angle, blip.dist)
          const visible = visibleBlips.has(blip.id)
          if (!visible) return null

          return (
            <g key={blip.id}>
              <circle
                cx={pos.x}
                cy={pos.y}
                r={blip.critical ? 4 : 3}
                fill={blip.critical ? '#ef4444' : '#00ff88'}
                style={{ animation: blip.critical ? 'dotPulse 1s ease-out infinite' : 'dotPulse 2s ease-out infinite' }}
              />
              <circle cx={pos.x} cy={pos.y} r={blip.critical ? 3 : 2} fill={blip.critical ? '#ef4444' : '#00ff88'} />
              <text x={pos.x + 8} y={pos.y + 4} fill={blip.critical ? '#ef4444' : '#00ff88'} fontSize="7" fontFamily="monospace" opacity="0.8">
                {blip.critical ? `${blip.name}⚠` : blip.name}
              </text>
            </g>
          )
        })}

        {Array.from({ length: 36 }, (_, i) => {
          const a = ((i * 10 - 90) * Math.PI) / 180
          const inner = RADIUS - 6
          const outer = RADIUS
          return (
            <line
              key={i}
              x1={CENTER.x + Math.cos(a) * inner}
              y1={CENTER.y + Math.sin(a) * inner}
              x2={CENTER.x + Math.cos(a) * outer}
              y2={CENTER.y + Math.sin(a) * outer}
              stroke="rgba(0,255,136,0.3)"
              strokeWidth={i % 9 === 0 ? 2 : 0.5}
            />
          )
        })}

        {[0, 90, 180, 270].map((deg, i) => {
          const a = ((deg - 90) * Math.PI) / 180
          const r = RADIUS + 15
          return (
            <text key={i} x={CENTER.x + Math.cos(a) * r - 8} y={CENTER.y + Math.sin(a) * r + 4} fill="rgba(0,255,136,0.4)" fontSize="8" fontFamily="monospace">
              {deg}°
            </text>
          )
        })}
      </svg>
    </div>
  )
}
