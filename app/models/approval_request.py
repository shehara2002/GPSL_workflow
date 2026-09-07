import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Numeric, Text, DateTime, ForeignKey, Sequence
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.database import Base

# Sequence for the human-readable AP-YYYY-NNNN ref.
# Starts at 1401 so it continues after the demo fixture data.
ap_ref_seq = Sequence("ap_ref_seq", start=1401, increment=1, schema="public")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    __table_args__ = {"schema": "public"}

    # Primary key — UUID so it is safe to expose in URLs
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Human-readable reference (AP-2026-NNNN)
    ref = Column(String(32), unique=True, nullable=False, index=True)

    # Core request fields
    title         = Column(String(120),     nullable=False)
    category      = Column(String(32),      nullable=False)
    entity        = Column(String(100),     nullable=False)
    province      = Column(String(50),      nullable=False)
    site          = Column(String(200),     nullable=True)
    currency      = Column(String(8),       nullable=False, default="LKR")
    amount        = Column(Numeric(18, 2),  nullable=False, default=0)
    amount_lkr    = Column(Numeric(18, 2),  nullable=False, default=0)
    justification = Column(Text,            nullable=False)

    # Workflow state
    status      = Column(String(20),  nullable=False, default="review", index=True)
    stage_index = Column(Integer,     nullable=False, default=0)

    # JSONB payloads — chain[], documents[], auditTrail[]
    chain       = Column(JSONB, nullable=False, default=list)
    documents   = Column(JSONB, nullable=False, default=list)
    audit_trail = Column(JSONB, nullable=False, default=list)

    # Requester (denormalized for fast display without JOINs)
    requester_id    = Column(Integer, ForeignKey("public.users.user_id"), nullable=False, index=True)
    requester_name  = Column(String(255), nullable=False)
    requester_email = Column(String(255), nullable=False)

    raised_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ApprovalRequest(ref='{self.ref}', status='{self.status}')>"
