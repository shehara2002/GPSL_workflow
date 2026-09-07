from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email: str
    password: str
    remember: Optional[bool] = False

    model_config = ConfigDict(
        populate_by_name=True
    )


class LoginResponse(BaseModel):
    success: bool = True
    message: str = "Sign in successful"
    mfa_required: bool = Field(False, alias="mfaRequired")
    user: Optional[UserResponse] = None
    token: Optional[str] = None
    redirect_url: str = Field("/home", alias="redirectUrl")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )


class SignupResponse(BaseModel):
    request_id: str = Field(..., alias="requestId")
    status: str = "active"
    message: str = "Account successfully created."
    user: Optional[UserResponse] = None

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
