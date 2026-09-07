import re
from typing import Optional, List, Union, Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def parse_phone_to_int_array(v: Any) -> Optional[List[int]]:
    """Helper to validate exactly 10 integers and convert into integer[] for PostgreSQL."""
    if v is None or v == "":
        return None

    # Extract all digit characters
    if isinstance(v, list):
        digits = "".join(re.findall(r"\d", "".join(str(x) for x in v)))
    else:
        digits = "".join(re.findall(r"\d", str(v)))

    if len(digits) == 11 and digits.startswith("94"):
        digits = "0" + digits[2:]

    if len(digits) != 10:
        raise ValueError("Phone number must contain exactly 10 integers (e.g. 0771234567).")

    # Store in PostgreSQL integer[] safely within 32-bit int bounds
    val = int(digits)
    if val <= 2147483647:
        return [val]
    else:
        return [int(digits[:5]), int(digits[5:])]


class UserBase(BaseModel):
    first_name: Optional[str] = Field(None, alias="firstName")
    email: Optional[str] = None
    job_title: Optional[str] = Field(None, alias="jobTitle")
    phone: Optional[Union[List[int], str, int]] = None

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )


class UserCreate(BaseModel):
    first_name: str = Field(..., alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    email: str
    password: str
    phone: Optional[Union[List[int], str, int]] = None
    job_title: Optional[str] = Field(None, alias="jobTitle")
    line_manager_email: Optional[str] = Field(None, alias="lineManagerEmail")
    entity: Optional[str] = None
    role: Optional[str] = None
    limit_lkr: Optional[Union[str, int]] = Field(None, alias="limitLKR")
    provinces: Optional[List[str]] = None
    reason: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: Any) -> Optional[List[int]]:
        return parse_phone_to_int_array(v)

    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.first_name.strip()


class UserResponse(BaseModel):
    user_id: int
    first_name: Optional[str] = Field(None, alias="firstName")
    email: Optional[str] = None
    phone: Optional[List[int]] = None
    job_title: Optional[str] = Field(None, alias="jobTitle")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
