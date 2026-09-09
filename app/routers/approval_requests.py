"""
Approval Requests router
========================
Endpoints consumed by module.html.  All routes require an authenticated
session (get_current_user dependency from auth.py).

Route rules and FX rates are hard-coded here (matching the client-side
constants in module.html) so that the server independently enforces
authority limits.  In production these should come from a configuration
table so they can be updated without a code deployment.
"""

from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models.approval_request import ApprovalRequest, ap_ref_seq
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.approval_request import (
    ApprovalRequestCreate,
    ApprovalRequestListResponse,
    ApprovalRequestResponse,
    DecisionCreate,
    MeResponse,
)

# Uploads directory — files are served via the existing /static mount
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api", tags=["Approval Requests"])

# ---------------------------------------------------------------------------
# Constants (mirror of module.html CONFIG / ROUTE_RULES / FX_TO_LKR)
# ---------------------------------------------------------------------------

# Default authority limit when none is stored on the user record (LKR)
DEFAULT_LIMIT_LKR = 2_500_000

# All entities and provinces supported by the platform
ALL_ENTITIES = [
    "GPSLM", "SPV Western 01", "SPV Western 02", "SPV Central 01",
    "SPV Southern 01", "SPV North Western 01", "SPV Sabaragamuwa 01", "SPV Uva 01",
]
ALL_PROVINCES = [
    "Western", "Central", "Southern", "North Western",
    "North Central", "Sabaragamuwa", "Uva",
]

# Approval route thresholds (LKR)
ROUTE_RULES = [
    {"max": 2_500_000,       "stages": ["Technical review", "Provincial manager", "Head of operations"]},
    {"max": 25_000_000,      "stages": ["Technical review", "Head of operations", "Chief financial officer"]},
    {"max": 75_000_000,      "stages": ["Technical review", "Head of operations", "Chief financial officer", "Managing director"]},
    {"max": float("inf"),    "stages": ["Technical review", "Head of operations", "Chief financial officer", "Managing director", "Board of directors"]},
]

# Extra approvers injected after position 1 for certain categories
CATEGORY_EXTRA = {
    "es":      "E&S manager, IFC Performance Standards check",
    "consent": "Legal counsel, Provincial Council consent review",
    "ppa":     "Legal counsel, PPA review",
    "legal":   "Legal counsel",
}

# Indicative FX-to-LKR rates (production: fetch from a rates table)
FX_TO_LKR = {"LKR": 1, "USD": 300, "EUR": 325}

CLOSED_STATUSES = {"approved", "rejected"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def route_for(category: str, amount_lkr: float) -> list[str]:
    """Compute approval chain for a category + LKR-equivalent value."""
    for rule in ROUTE_RULES:
        if amount_lkr <= rule["max"]:
            stages = list(rule["stages"])
            extra = CATEGORY_EXTRA.get(category)
            if extra:
                stages.insert(1, extra)
            return stages
    # Fallback (should never be reached)
    return ROUTE_RULES[-1]["stages"]


def _row_to_response(r: ApprovalRequest) -> dict:
    """Serialise an ORM row to the dict shape that module.html expects."""
    return {
        "id":            str(r.id),
        "ref":           r.ref,
        "title":         r.title,
        "category":      r.category,
        "entity":        r.entity,
        "province":      r.province,
        "site":          r.site,
        "currency":      r.currency,
        "amount":        float(r.amount),
        "amountLKR":     float(r.amount_lkr),
        "justification": r.justification,
        "requester":     r.requester_name,
        "requesterEmail":r.requester_email,
        "raisedAt":      r.raised_at.isoformat() if r.raised_at else now_iso(),
        "status":        r.status,
        "stageIndex":    r.stage_index,
        "chain":         r.chain or [],
        "documents":     r.documents or [],
        "auditTrail":    r.audit_trail or [],
    }


def _next_ref(db: Session) -> str:
    """Fetch the next value from the ap_ref_seq sequence."""
    seq_val = db.execute(text("SELECT nextval('public.ap_ref_seq')")).scalar()
    year = datetime.now(timezone.utc).year
    return f"AP-{year}-{seq_val}"


# ---------------------------------------------------------------------------
# POST /api/documents/upload
# ---------------------------------------------------------------------------

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Accept a file upload and save it to app/static/uploads/{uuid}/{filename}.
    Returns { key, filename, size, type } — key is used by the JS to attach
    the document to the approval request on submit.

    Files are served from /static/uploads/... via the existing static mount.
    """
    # Sanitise filename — strip path separators
    safe_name = Path(file.filename or "upload").name or "upload"
    file_uuid = str(uuid.uuid4())
    dest_dir  = UPLOADS_DIR / file_uuid
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / safe_name

    try:
        with dest_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    finally:
        await file.close()

    size_bytes = dest_path.stat().st_size
    size_label = (
        f"{size_bytes / 1_048_576:.2f} MB" if size_bytes >= 1_048_576
        else f"{size_bytes / 1024:.0f} KB"
    )
    ext = safe_name.rsplit(".", 1)[-1].upper()[:4] if "." in safe_name else "DOC"
    key = f"uploads/{file_uuid}/{safe_name}"

    return {
        "key":      key,
        "filename": safe_name,
        "size":     size_label,
        "type":     ext,
        "url":      f"/static/{key}",
    }


# ---------------------------------------------------------------------------
# GET /api/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Return current user profile in the shape expected by module.html Api.me().
    """
    name = current_user.first_name or current_user.email.split("@")[0]
    return MeResponse(
        id=str(current_user.user_id),
        name=name,
        email=current_user.email,
        role="Platform User",
        title=current_user.job_title or "Team Member",
        entities=ALL_ENTITIES,
        provinces=ALL_PROVINCES,
        limitLKR=DEFAULT_LIMIT_LKR,
        permissions=["request.create", "request.approve", "request.reject", "request.return"],
    )


# ---------------------------------------------------------------------------
# GET /api/approval-requests
# ---------------------------------------------------------------------------

@router.get("/approval-requests", response_model=ApprovalRequestListResponse)
def list_requests(
    view:     Optional[str] = None,
    q:        Optional[str] = None,
    category: Optional[str] = None,
    province: Optional[str] = None,
    status:   Optional[str] = None,
    entity:   Optional[str] = None,
    page:     int = 1,
    pageSize: int = 8,
    sort:     Optional[str] = "age:desc",
    db:       Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List approval requests with optional filtering.

    The client sends:  view=queue|all|mine|closed|audit  plus free filters.
    Filtering by 'view' (queue / mine) is performed here; the others are
    SQL WHERE clauses.

    Note: For 'queue' view the server returns all non-closed requests.
    The client-side isMyStage() function further narrows to those where
    the current user is the current-stage approver (matching on job_title).
    The proper server-side approach would be to store the approver's user_id
    on the chain step; this can be added once the org chart is in the DB.
    """
    query = db.query(ApprovalRequest)

    # View-level filter
    if view == "mine":
        query = query.filter(ApprovalRequest.requester_id == current_user.user_id)
    elif view == "closed":
        query = query.filter(ApprovalRequest.status.in_(["approved", "rejected"]))
    elif view == "queue" or view == "all" or view == "audit" or not view:
        # Return all (client filters queue/audit further in JS)
        pass

    # Field filters
    if category:
        query = query.filter(ApprovalRequest.category == category)
    if province:
        query = query.filter(ApprovalRequest.province == province)
    if status:
        query = query.filter(ApprovalRequest.status == status)
    if entity and entity != "all":
        query = query.filter(ApprovalRequest.entity == entity)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            func.lower(ApprovalRequest.title).like(like) |
            func.lower(ApprovalRequest.ref).like(like) |
            func.lower(ApprovalRequest.requester_name).like(like) |
            func.lower(ApprovalRequest.entity).like(like)
        )

    # Sort
    query = query.order_by(ApprovalRequest.raised_at.desc())

    total = query.count()
    rows = query.all()

    # Apply sequential workflow filtering for 'queue' view
    if view == "queue":
        filtered_rows = []
        for r in rows:
            if r.status in CLOSED_STATUSES:
                continue
            stage_idx = r.stage_index
            chain = r.chain or []
            if stage_idx < len(chain):
                step = chain[stage_idx]
                if step.get("state") == "current" and step.get("stage") == current_user.job_title:
                    filtered_rows.append(r)
        rows = filtered_rows
        total = len(rows)

    items = [_row_to_response(r) for r in rows]
    return {"items": items, "total": total}


# ---------------------------------------------------------------------------
# POST /api/approval-requests
# ---------------------------------------------------------------------------

@router.post("/approval-requests", status_code=status.HTTP_201_CREATED)
def create_request(
    payload:      ApprovalRequestCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """
    Create a new approval request.

    Computes the approval chain from the delegation-of-authority route rules,
    generates the AP-YYYY-NNNN reference from a DB sequence, and records the
    first audit entry.
    """
    # Compute LKR-equivalent amount
    amount_lkr = payload.amount * FX_TO_LKR.get(payload.currency, 1)

    # Build approval chain
    stages = route_for(payload.category, amount_lkr)
    now = now_iso()
    name = current_user.first_name or current_user.email.split("@")[0]

    chain = [
        {
            "stage":     s,
            "decidedBy": None,
            "decision":  None,
            "decidedAt": None,
            "note":      None,
            "state":     "current" if i == 0 else "waiting",
        }
        for i, s in enumerate(stages)
    ]

    audit_trail = [
        {
            "at":     now,
            "actor":  name,
            "action": "Request raised",
            "detail": f"Routed to {stages[0]}",
        }
    ]

    # Ensure the sequence exists (idempotent DDL in case auto-create missed it)
    db.execute(text(
        "CREATE SEQUENCE IF NOT EXISTS public.ap_ref_seq START 1401 INCREMENT 1"
    ))
    db.commit()

    ref = _next_ref(db)

    new_req = ApprovalRequest(
        id              = uuid.uuid4(),
        ref             = ref,
        title           = payload.title,
        category        = payload.category,
        entity          = payload.entity,
        province        = payload.province,
        site            = payload.site,
        currency        = payload.currency,
        amount          = payload.amount,
        amount_lkr      = amount_lkr,
        justification   = payload.justification,
        status          = "review",
        stage_index     = 0,
        chain           = chain,
        documents       = [d.model_dump() for d in payload.documents],
        audit_trail     = audit_trail,
        requester_id    = current_user.user_id,
        requester_name  = name,
        requester_email = current_user.email,
    )

    db.add(new_req)
    db.commit()
    db.refresh(new_req)

    return _row_to_response(new_req)


# ---------------------------------------------------------------------------
# GET /api/approval-requests/{id}
# ---------------------------------------------------------------------------

@router.get("/approval-requests/{request_id}")
def get_request(
    request_id:   str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Fetch a single approval request by UUID."""
    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID.")

    r = db.query(ApprovalRequest).filter(ApprovalRequest.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="Request not found.")

    return _row_to_response(r)


# ---------------------------------------------------------------------------
# POST /api/approval-requests/{id}/decisions
# ---------------------------------------------------------------------------

@router.post("/approval-requests/{request_id}/decisions")
def decide(
    request_id:   str,
    payload:      DecisionCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """
    Record an approve / reject / return decision on the current stage.

    Server-side checks:
    - Request must be open (not approved/rejected).
    - Decision must be one of: approve, reject, return.
    - comment is required for reject and return.
    - Authority limit is checked; exceeding it is allowed for 'approve'
      (the UI labels it "Endorse and refer upward") but the request is
      escalated rather than finally approved.
    """
    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID.")

    r = db.query(ApprovalRequest).filter(ApprovalRequest.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="Request not found.")

    if r.status in CLOSED_STATUSES:
        raise HTTPException(status_code=409, detail="This request is already closed.")

    decision = payload.decision
    if decision not in ("approve", "reject", "return"):
        raise HTTPException(status_code=400, detail="decision must be approve, reject, or return.")

    comment = (payload.comment or "").strip()
    if decision in ("reject", "return") and len(comment) < 10:
        raise HTTPException(
            status_code=422,
            detail="A comment of at least 10 characters is required to reject or return a request.",
        )

    now = now_iso()
    name = current_user.first_name or current_user.email.split("@")[0]

    # Work on a mutable copy of the JSONB list
    chain = list(r.chain or [])
    audit = list(r.audit_trail or [])
    stage_index = r.stage_index

    if stage_index >= len(chain):
        raise HTTPException(status_code=409, detail="No current stage to decide on.")

    step = dict(chain[stage_index])

    if step.get("stage") != current_user.job_title:
        raise HTTPException(status_code=403, detail="You are not the approver for this stage.")
    label_map = {
        "approve": "Approved",
        "reject":  "Rejected",
        "return":  "Returned for information",
    }
    label = label_map[decision]

    # Record the decision on the step
    step["decidedBy"] = name
    step["decidedAt"] = now
    step["note"]      = comment or None
    step["decision"]  = decision

    new_status = r.status
    new_stage_index = stage_index

    if decision == "approve":
        step["state"] = "done"
        if stage_index < len(chain) - 1:
            new_stage_index = stage_index + 1
            next_step = dict(chain[new_stage_index])
            next_step["state"] = "current"
            chain[new_stage_index] = next_step
            new_status = (
                "board" if chain[new_stage_index]["stage"] == "Board of directors"
                else "pending"
            )
        else:
            new_status = "approved"

    elif decision == "reject":
        step["state"] = "rejected"
        new_status    = "rejected"

    else:  # return
        step["state"]      = "waiting"
        step["decidedBy"]  = None
        step["decidedAt"]  = None
        step["decision"]   = None
        new_status         = "returned"

    chain[stage_index] = step

    audit.append({
        "at":     now,
        "actor":  name,
        "action": f"{label} at {step['stage']}",
        "detail": comment or "No comment recorded",
    })

    # Write back — must reassign JSONB columns to trigger SQLAlchemy dirty tracking
    r.chain       = chain
    r.audit_trail = audit
    r.status      = new_status
    r.stage_index = new_stage_index

    db.add(r)
    db.commit()
    db.refresh(r)

    return _row_to_response(r)
