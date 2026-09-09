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

class RecommendationStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    MODIFIED = "modified"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


class ApprovalActionType(str, Enum):
    APPROVE = "approve"
    MODIFY = "modify"
    REJECT = "reject"


class NotificationChannel(str, Enum):
    EMAIL = "email"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"