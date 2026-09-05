from enum import Enum


class ElevationTier(str, Enum):
    HIGH = "high"
    MID = "mid"
    LOW = "low"