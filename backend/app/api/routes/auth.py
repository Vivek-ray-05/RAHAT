from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.rate_limit import limiter
from app.db.session import get_session
from app.schemas.auth import LoginRequest, OtpRequestRequest, OtpVerifyRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, session: Session = Depends(get_session)):
    try:
        user = auth_service.authenticate_password(session, payload.email, payload.password, payload.role)
    except auth_service.AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    token = auth_service.issue_token(user)
    return TokenResponse(access_token=token, user_id=user.id, role=user.role, zone_id=user.zone_id)


@router.post("/otp/request")
@limiter.limit("5/minute")
def request_otp(request: Request, payload: OtpRequestRequest):
    try:
        code = auth_service.request_otp(payload.phone)
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))

    # Only echo the code back in dev mode -- a real provider (Phase 6)
    # would send it via SMS instead and return nothing sensitive here.
    from app.config import settings
    return {"dev_otp": code} if settings.DEV_MODE else {"detail": "OTP sent"}


@router.post("/otp/verify", response_model=TokenResponse)
@limiter.limit("10/minute")
def verify_otp(request: Request, payload: OtpVerifyRequest, session: Session = Depends(get_session)):
    try:
        user = auth_service.verify_otp(session, payload.phone, payload.code)
    except auth_service.AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    token = auth_service.issue_token(user)
    return TokenResponse(access_token=token, user_id=user.id, role=user.role, zone_id=user.zone_id)