from enum import Enum


class ElevationTier(str, Enum):
    HIGH = "high"
    MID = "mid"
    LOW = "low"


class SimulationStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"   


class CitizenReportStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"    


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RouteStatus(str, Enum):
    USABLE = "usable"
    DEGRADED = "degraded"
    BLOCKED = "blocked"

