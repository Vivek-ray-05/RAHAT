import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../api/client'
import { useSocket } from '../context/SocketContext'

const BENGALURU_CENTER = [12.9716, 77.5946]

const RISK_COLOR = (risk) => {
  if (risk == null) return '#6b7280' // gray -- unknown
  if (risk >= 7) return '#ef4444' // red
  if (risk >= 5) return '#f59e0b' // amber
  if (risk >= 3) return '#eab308' // yellow
  return '#22c55e' // green
}

function zoneIcon(risk) {
  const color = RISK_COLOR(risk)
  return L.divIcon({
    className: 'rahat-zone-marker',
    html: `<div style="width:14px;height:14px;background:${color};border-radius:50%;border:2px solid #0a0a0a;box-shadow:0 0 8px ${color};"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

const shelterIcon = L.divIcon({
  className: 'rahat-shelter-marker',
  html: `<div style="width:14px;height:14px;background:#ffffff;border-radius:3px;border:2px solid #22c55e;box-shadow:0 0 8px #ffffff;"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7],
})

/**
 * One Leaflet map, reused across every role that needs a real
 * evacuation-routing view. Every marker/line comes from a real
 * backend row (Zone/Shelter with real coordinates, RouteOption,
 * Road) -- nothing here is fabricated for display.
 *
 * When `simulationRunId` is given, the route layer refetches on every
 * new tick from the shared tick WebSocket (SocketContext) -- the page
 * that owns this map is responsible for calling connect(runId) itself
 * (SocketContext supports only one live connection at a time), this
 * component only reacts to `latestTick` changing.
 */
export default function EvacuationMap({
  zones = [],
  shelters = [],
  roads = null,
  simulationRunId = null,
  onBlockRoad = null,
  directionLine = null,
  height = '500px',
}) {
  const { latestTick } = useSocket()
  const [routes, setRoutes] = useState([])
  const [liveRoads, setLiveRoads] = useState(roads)

  useEffect(() => {
    setLiveRoads(roads)
  }, [roads])

  const zonesById = useMemo(() => Object.fromEntries(zones.map((z) => [z.id, z])), [zones])
  const sheltersById = useMemo(() => Object.fromEntries(shelters.map((s) => [s.id, s])), [shelters])

  useEffect(() => {
    if (!simulationRunId) return
    let cancelled = false

    async function load() {
      try {
        const [routesData, roadsData] = await Promise.all([
          api.get(`/routes?simulation_run_id=${simulationRunId}`),
          roads !== null ? api.get('/roads') : Promise.resolve(null),
        ])
        if (!cancelled) {
          setRoutes(routesData)
          if (roadsData !== null) setLiveRoads(roadsData)
        }
      } catch {
        // A transient failure to refresh the live layer shouldn't crash
        // the map -- it just keeps showing the last good data.
      }
    }

    load()
    return () => { cancelled = true }
    // Re-run on every new tick (latestTick?.id changing), not just on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [simulationRunId, latestTick?.id])

  return (
    <div style={{ height, width: '100%' }} className="border border-gray-800">
      <MapContainer center={BENGALURU_CENTER} zoom={11} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; CARTO'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {liveRoads && liveRoads.map((road) => {
          const from = zonesById[road.from_zone_id]
          const to = zonesById[road.to_zone_id]
          if (!from?.center_lat || !to?.center_lat) return null
          return (
            <Polyline
              key={`road-${road.id}`}
              positions={[[from.center_lat, from.center_lon], [to.center_lat, to.center_lon]]}
              color={road.is_blocked ? '#ef4444' : '#374151'}
              weight={road.is_blocked ? 4 : 1.5}
              opacity={road.is_blocked ? 0.9 : 0.4}
              dashArray={road.is_blocked ? undefined : '4 6'}
            >
              <Popup>
                <div className="text-xs font-mono">
                  <div>{from.name} &harr; {to.name}</div>
                  <div>{road.is_blocked ? 'BLOCKED' : 'open'}{road.distance_km ? ` // ${road.distance_km} km` : ''}</div>
                  {onBlockRoad && !road.is_blocked && (
                    <button
                      onClick={() => onBlockRoad(road.id)}
                      className="mt-1 text-red-400 border border-red-500/50 px-2 py-0.5"
                    >
                      BLOCK ROAD
                    </button>
                  )}
                </div>
              </Popup>
            </Polyline>
          )
        })}

        {routes.map((route) => {
          const from = zonesById[route.from_zone_id]
          const to = sheltersById[route.to_shelter_id]
          if (!from?.center_lat || !to?.lat) return null
          return (
            <Polyline
              key={`route-${route.id}`}
              positions={[[from.center_lat, from.center_lon], [to.lat, to.lon]]}
              color={route.status === 'usable' ? '#60a5fa' : '#ef4444'}
              weight={3}
              opacity={0.8}
              dashArray="8 6"
            >
              <Popup>
                <div className="text-xs font-mono">
                  <div>{from.name} &rarr; {to.name}</div>
                  <div>ETA {route.eta} min // {route.status}</div>
                </div>
              </Popup>
            </Polyline>
          )
        })}

        {directionLine && (
          <Polyline
            positions={[[directionLine.from.lat, directionLine.from.lon], [directionLine.to.lat, directionLine.to.lon]]}
            color="#22c55e"
            weight={4}
            opacity={0.9}
            dashArray="8 6"
          >
            {directionLine.label && (
              <Popup>
                <div className="text-xs font-mono">{directionLine.label}</div>
              </Popup>
            )}
          </Polyline>
        )}

        {zones.filter((z) => z.center_lat != null).map((zone) => (
          <Marker key={`zone-${zone.id}`} position={[zone.center_lat, zone.center_lon]} icon={zoneIcon(zone.flood_risk_base)}>
            <Popup>
              <div className="text-xs font-mono">
                <div className="font-bold">{zone.name}</div>
                <div>risk {zone.flood_risk_base != null ? zone.flood_risk_base.toFixed(1) : 'n/a'}</div>
              </div>
            </Popup>
          </Marker>
        ))}

        {shelters.filter((s) => s.lat != null).map((shelter) => (
          <Marker key={`shelter-${shelter.id}`} position={[shelter.lat, shelter.lon]} icon={shelterIcon}>
            <Popup>
              <div className="text-xs font-mono">
                <div className="font-bold">{shelter.name}</div>
                <div>{shelter.current_occupancy}/{shelter.capacity}</div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
