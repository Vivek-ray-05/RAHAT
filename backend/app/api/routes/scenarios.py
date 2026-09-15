from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import require_role
from app.core.roles import RoleEnum
from app.db.session import get_session
from app.models.scenario import Scenario
from app.models.user import User
from app.schemas.scenario import ScenarioResponse

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioResponse])
def list_scenarios(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.CENTRAL_COORDINATOR)),
):
    return session.exec(select(Scenario)).all()
