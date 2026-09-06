from enum import Enum


class ElevationTier(str, Enum):
    HIGH = "high"
    MID = "mid"
    LOW = "low"


class SimulationStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"   