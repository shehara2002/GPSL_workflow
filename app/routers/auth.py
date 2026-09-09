import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_reset_email
from app.core.security import hash_password, verify_password, create_session_token, verify_session_token
from app.database import get_db
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, SignupResponse
from app.schemas.user import UserCreate, UserResponse


router = APIRouter(
    tags=["Authentication"]
)


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Extract and verify user from session cookie or Bearer token header."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return None

    payload = verify_session_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    return db.query(User).filter(User.user_id == user_id).first()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Dependency that requires an authenticated user."""
    user = get_current_user_optional(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in."
        )
    return user


@router.post("/api/auth/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
@router.post("/api/v1/accounts/requests", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup_user(
    user_data: UserCreate,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Register a new user in PostgreSQL database, hash password with bcrypt,
    and create session.
    """
    clean_email = user_data.email.strip().lower()

    # Check if email is already taken
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for this email address. Please sign in."
        )

    # Hash the password
    hashed_pw = hash_password(user_data.password)

    # Prepare display name
    display_name = user_data.full_name or user_data.first_name

    # Create new User model instance matching PostgreSQL schema
    new_user = User(
        first_name=display_name,
        last_name=user_data.last_name,
        email=clean_email,
        password=hashed_pw,
        phone=user_data.phone,
        job_title=user_data.job_title or (user_data.role.title() if user_data.role else "Team Member"),
        line_manager_email=user_data.line_manager_email,
        entity=user_data.entity,
        role=user_data.role,
        limit_lkr=str(user_data.limit_lkr) if user_data.limit_lkr else None,
        provinces=user_data.provinces,
        reason=user_data.reason
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    request_ref = f"AR-2026-{new_user.user_id:04d}"
    new_user.request_ref = request_ref
    db.commit()

    # Generate session token and set cookie
    token = create_session_token(new_user.user_id, new_user.email)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )

    request_ref = f"AR-2026-{new_user.user_id:04d}"

    return SignupResponse(
        requestId=request_ref,
        status="active",
        message="Account created successfully!",
        user=UserResponse.model_validate(new_user)
    )


@router.post("/api/auth/login", response_model=LoginResponse)
@router.post("/api/v1/auth/login", response_model=LoginResponse)
def signin_user(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticate user against PostgreSQL users table, verifying password and
    issuing session cookie.
    """
    clean_email = login_data.email.strip().lower()

    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password."
        )

    # Issue session token
    expire_seconds = (
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 7
        if login_data.remember
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    token = create_session_token(user.user_id, user.email, expires_in_seconds=expire_seconds)

    # Set session cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=expire_seconds,
        samesite="lax"
    )

    return LoginResponse(
        success=True,
        message="Sign in successful",
        mfaRequired=False,
        user=UserResponse.model_validate(user),
        token=token,
        redirectUrl="/home"
    )


@router.get("/api/auth/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Fetch profile of the currently signed-in user."""
    return UserResponse.model_validate(current_user)


@router.post("/api/v1/auth/logout")
@router.post("/api/auth/logout")
def logout_user(response: Response):
    """Log out current user and clear session cookie."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax"
    )
    return {"success": True, "message": "Logged out successfully", "redirectUrl": "/signin"}


@router.post("/api/v1/auth/mfa/verify")
def mfa_verify_mock(request: Request, response: Response, db: Session = Depends(get_db)):
    """MFA verification endpoint."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=400, detail="No user found.")
    token = create_session_token(user.user_id, user.email)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return {"user": UserResponse.model_validate(user), "redirectUrl": "/home"}


@router.post("/api/v1/auth/password/reset-request")
@router.post("/api/auth/password/reset-request")
def password_reset_request(payload: dict, db: Session = Depends(get_db)):
    """
    Send a password-reset link to the supplied email address.

    Always returns 200 with the same message regardless of whether the email
    is registered (prevents email enumeration attacks).
    """
    email = (payload.get("email") or "").strip().lower()
    generic_response = {
        "sent": True,
        "message": "If this email is registered, password reset instructions have been sent."
    }

    if not email:
        return generic_response

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Silently succeed — do not reveal whether the account exists
        return generic_response

    # Generate a secure random token and persist it
    raw_token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)

    reset_token = PasswordResetToken(
        user_id=user.user_id,
        token=raw_token,
        expires_at=expires_at,
    )
    db.add(reset_token)
    db.commit()

    # Build the reset link and send the email
    reset_link = f"{settings.APP_BASE_URL}/reset-password?token={raw_token}"
    try:
        send_reset_email(to_email=user.email, reset_link=reset_link)
    except RuntimeError as exc:
        # Log loudly but don't expose internal errors to the caller
        import logging
        logging.getLogger(__name__).error("Reset email failed: %s", exc)

    return generic_response


@router.post("/api/v1/auth/password/reset-confirm")
@router.post("/api/auth/password/reset-confirm")
def password_reset_confirm(payload: dict, db: Session = Depends(get_db)):
    """
    Validate a password-reset token and update the user's password.

    Expects JSON body: { "token": "...", "password": "..." }
    """
    token_str = (payload.get("token") or "").strip()
    new_password = payload.get("password") or ""

    if not token_str or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both 'token' and 'password' are required."
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == token_str)
        .first()
    )

    if not reset_token or not reset_token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired. Please request a new one."
        )

    # Update the user's password
    user = db.query(User).filter(User.user_id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.password = hash_password(new_password)
    reset_token.used = True          # Mark token as consumed
    db.commit()

    return {"success": True, "message": "Your password has been updated. You can now sign in."}

