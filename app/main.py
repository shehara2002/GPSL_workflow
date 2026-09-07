from contextlib import asynccontextmanager
from pathlib import Path
import time
from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import Base, engine, get_db, test_connection
from app.routers import auth_router, users_router, approval_requests_router
from app.models import ApprovalRequest  # noqa: F401 — ensures table is registered with Base.metadata

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables if they don't exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[WARNING] Table creation check failed: {e}")

    # Test DB connection on startup with psycopg 3
    result = test_connection()
    if result.get("status") == "connected":
        print(f"[SUCCESS] Connected to database: {result.get('database')} on {result.get('host')}:{result.get('port')} using driver '{result.get('driver')}'")
    else:
        print(f"[WARNING] Database connection failed on startup: {result.get('message')}")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Greenpower SL Approvals Workflow with PostgreSQL & Psycopg 3 Driver",
    lifespan=lifespan
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(approval_requests_router)

STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount templates folder for direct static asset access if needed
if TEMPLATES_DIR.exists():
    app.mount("/static_templates", StaticFiles(directory=str(TEMPLATES_DIR)), name="static_templates")


# =========================================================================
# Page Routes with Full Navigation
# =========================================================================

@app.get("/", include_in_schema=False)
def index_redirect(request: Request):
    """Root route redirects to signin or home depending on session."""
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if session_cookie:
        return RedirectResponse(url="/home")
    return RedirectResponse(url="/signin")


@app.get("/signin", include_in_schema=False)
@app.get("/login", include_in_schema=False)
@app.get("/signin.html", include_in_schema=False)
@app.get("/login.html", include_in_schema=False)
def serve_signin_page():
    """Serves the Sign In HTML page."""
    signin_path = TEMPLATES_DIR / "signin" / "signin.html"
    if not signin_path.exists():
        raise HTTPException(status_code=404, detail="Signin template not found")
    return FileResponse(str(signin_path), media_type="text/html")


@app.get("/signup", include_in_schema=False)
@app.get("/signup.html", include_in_schema=False)
def serve_signup_page():
    """Serves the Sign Up HTML page."""
    signup_path = TEMPLATES_DIR / "signup" / "signup.html"
    if not signup_path.exists():
        raise HTTPException(status_code=404, detail="Signup template not found")
    return FileResponse(str(signup_path), media_type="text/html")


@app.get("/home", include_in_schema=False)
@app.get("/home.html", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
def serve_home_page():
    """Serves the Home / Modules Dashboard HTML page."""
    home_path = TEMPLATES_DIR / "home" / "home.html"
    if not home_path.exists():
        raise HTTPException(status_code=404, detail="Home template not found")
    return FileResponse(str(home_path), media_type="text/html")


@app.get("/module", include_in_schema=False)
@app.get("/module.html", include_in_schema=False)
def serve_module_page():
    """Serves the Module / Approvals Workflow HTML page."""
    module_path = TEMPLATES_DIR / "module" / "module.html"
    if not module_path.exists():
        raise HTTPException(status_code=404, detail="Module template not found")
    return FileResponse(str(module_path), media_type="text/html")


@app.get("/reset-password", include_in_schema=False)
def serve_reset_password_page():
    """Serves the Reset Password HTML page (linked from the password-reset email)."""
    page_path = TEMPLATES_DIR / "reset_password" / "reset_password.html"
    if not page_path.exists():
        raise HTTPException(status_code=404, detail="Reset password template not found")
    return FileResponse(str(page_path), media_type="text/html")



# =========================================================================
# Health Check Endpoint
# =========================================================================

@app.get("/api/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint that verifies server and database connectivity and latency.
    """
    t0 = time.time()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = round((time.time() - t0) * 1000, 2)
        return {
            "status": "healthy",
            "server": "online",
            "database": {
                "status": "connected",
                "engine": "PostgreSQL",
                "driver": engine.url.drivername,
                "database_name": engine.url.database,
                "host": engine.url.host,
                "port": engine.url.port,
                "latency_ms": latency_ms
            },
            "uptime_seconds": round(time.time() - START_TIME, 1)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": {
                    "status": "disconnected",
                    "error": str(e)
                }
            }
        )
