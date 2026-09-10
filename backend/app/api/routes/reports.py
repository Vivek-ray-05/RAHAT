from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.roles import RoleEnum
from app.db.session import get_session
from app.models.simulation import SimulationRun
from app.models.user import User
from app.schemas.report import PostEventReport
from app.services import report_service
from app.api.deps import require_role

router = APIRouter(prefix="/reports", tags=["reports"])

# Same operational-roles gate as roads.py/zones.py's route data --
# a citizen has no UI that needs this, and the report surfaces the
# reasoning and reviewer identity behind every recommendation.
_operational_roles = require_role(RoleEnum.NDRF, RoleEnum.ZONE_ADMIN, RoleEnum.CENTRAL_COORDINATOR)


@router.get("/{run_id}", response_model=PostEventReport)
def get_report(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(_operational_roles),
):
    run = session.get(SimulationRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation run not found")

    # Same scoping as GET /recommendations: a zone admin sees only
    # their own zone's slice of the run, everyone else sees it all.
    zone_id = current_user.zone_id if current_user.role == RoleEnum.ZONE_ADMIN else None
    return report_service.build_report(session, run, zone_id=zone_id)
