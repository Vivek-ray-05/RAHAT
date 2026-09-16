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

    # Only echo the code back in dev mode or for an allowlisted demo
    # phone number -- a real provider (Phase 6) would send it via SMS
    # instead and return nothing sensitive here.
    from app.config import settings
    show_code = settings.DEV_MODE or auth_service.is_demo_otp_phone(payload.phone)
    return {"dev_otp": code} if show_code else {"detail": "OTP sent"}


@router.post("/otp/verify", response_model=TokenResponse)
@limiter.limit("10/minute")
def verify_otp(request: Request, payload: OtpVerifyRequest, session: Session = Depends(get_session)):
    try:
        user = auth_service.verify_otp(session, payload.phone, payload.code)
    except auth_service.AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    token = auth_service.issue_token(user)
    return TokenResponse(access_token=token, user_id=user.id, role=user.role, zone_id=user.zone_id)