from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from app.database import Base


class PasswordResetToken(Base):
    """
    Stores one-time password-reset tokens.

    A new row is inserted every time the user requests a reset.
    Old / used tokens are harmless — they will never pass the
    `used=False` and `expires_at > now()` checks.
    """
    __tablename__ = "password_reset_tokens"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("public.users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def is_valid(self) -> bool:
        """Returns True when the token has not been used and has not expired."""
        return not self.used and self.expires_at > datetime.utcnow()
