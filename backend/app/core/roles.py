from enum import Enum


class RoleEnum(str, Enum):
    CENTRAL_COORDINATOR = "central_coordinator"
    ZONE_ADMIN = "zone_admin"
    NDRF = "ndrf"
    CITIZEN = "citizen"
