from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# /me  response
# ---------------------------------------------------------------------------

class MeResponse(BaseModel):
    """Shape expected by module.html Api.me()"""
    id: str
    name: str
    email: str
    role: str
    title: str
    entities: List[str]
    provinces: List[str]
    limit_lkr: int = Field(..., alias="limitLKR")
    permissions: List[str]

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Approval request schemas
# ---------------------------------------------------------------------------

class ChainStep(BaseModel):
    stage: str
    decided_by: Optional[str]    = Field(None, alias="decidedBy")
    decision:   Optional[str]    = None
    decided_at: Optional[str]    = Field(None, alias="decidedAt")
    note:       Optional[str]    = None
    state:      str              = "waiting"

    model_config = ConfigDict(populate_by_name=True)


class DocumentItem(BaseModel):
    name: str
    size: Optional[str] = None
    type: Optional[str] = None
    key:  Optional[str] = None


class AuditEntry(BaseModel):
    at:     str
    actor:  str
    action: str
    detail: str


class ApprovalRequestCreate(BaseModel):
    """Payload sent from the module.html new-request form."""
    title:         str
    category:      str
    entity:        str
    province:      str
    site:          Optional[str]          = None
    currency:      str                    = "LKR"
    amount:        float                  = 0
    amount_lkr:    float                  = Field(0, alias="amountLKR")
    justification: str
    documents:     List[DocumentItem]     = Field(default_factory=list)
    document_keys: List[str]              = Field(default_factory=list, alias="documentKeys")

    model_config = ConfigDict(populate_by_name=True)


class ApprovalRequestResponse(BaseModel):
    """Shape expected by module.html for every request object."""
    id:               str
    ref:              str
    title:            str
    category:         str
    entity:           str
    province:         str
    site:             Optional[str]
    currency:         str
    amount:           float
    amount_lkr:       float        = Field(..., alias="amountLKR")
    justification:    str
    requester:        str
    requester_email:  str          = Field(..., alias="requesterEmail")
    raised_at:        str          = Field(..., alias="raisedAt")
    status:           str
    stage_index:      int          = Field(..., alias="stageIndex")
    chain:            List[Dict[str, Any]]
    documents:        List[Dict[str, Any]]
    audit_trail:      List[Dict[str, Any]] = Field(..., alias="auditTrail")

    model_config = ConfigDict(populate_by_name=True)


class ApprovalRequestListResponse(BaseModel):
    items: List[ApprovalRequestResponse]
    total: int


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

class DecisionCreate(BaseModel):
    decision: str           # "approve" | "reject" | "return"
    comment:  Optional[str] = ""
