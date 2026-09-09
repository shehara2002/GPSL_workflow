# Greenpower SL Approvals Workflow - Authentication & User Management

A modern, high-performance web application and backend API for user registration, authentication, and workflow approvals management built with **FastAPI**, **PostgreSQL**, **SQLAlchemy ORM** using the **Psycopg 3** binary driver, and **Pydantic 2 Settings**.

---

## 🛠️ Technology Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **Database**: [PostgreSQL](https://www.postgresql.org/)
- **Database Driver**: [Psycopg 3 (`psycopg[binary]`)](https://www.psycopg.org/psycopg3/)
- **ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Data Validation & Settings**: [Pydantic 2](https://docs.pydantic.dev/) & [Pydantic-Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Password Security**: [Bcrypt](https://pypi.org/project/bcrypt/) password hashing
- **Frontend / UI**: Vanilla HTML5, CSS3 design system, Vanilla JavaScript with responsive navigation

---

## 🗄️ Database Schema

The system connects to the `public.users` table in PostgreSQL:

```sql
CREATE TABLE IF NOT EXISTS public.users
(
    user_id integer NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
    first_name character varying(255) COLLATE pg_catalog."default",
    email character varying(255) COLLATE pg_catalog."default",
    password character varying(255) COLLATE pg_catalog."default",
    phone integer[],
    job_title character varying(255) COLLATE pg_catalog."default",
    CONSTRAINT user_pkey PRIMARY KEY (user_id)
);
```

---

## 📂 Project Structure

```text
GPSL_Workflow/
│
├── .env                       # Environment variables (DB connection, secret key)
├── README.md                  # Project documentation
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI entry point & page routes
│   │
│   ├── core/                  # Core configuration & security
│   │   ├── __init__.py
│   │   ├── config.py          # Pydantic 2 BaseSettings
│   │   └── security.py        # Bcrypt hashing & HMAC session tokens
│   │
│   ├── database/              # Database connectivity
│   │   ├── __init__.py
│   │   └── connection.py      # SQLAlchemy engine with psycopg 3 driver & pool
│   │
│   ├── models/                # SQLAlchemy ORM Models
│   │   ├── __init__.py
│   │   ├── approval_request.py# Approval request model
│   │   ├── password_reset.py  # Password reset token model
│   │   └── user.py            # User model matching public.users table
│   │
│   ├── schemas/               # Pydantic 2 Validation Schemas
│   │   ├── __init__.py
│   │   ├── auth.py            # LoginRequest, LoginResponse, SignupResponse
│   │   └── user.py            # UserCreate, UserResponse, phone int[] parser
│   │
│   ├── routers/               # API Routers
│   │   ├── __init__.py
│   │   ├── approval_requests.py # /api/approval-requests endpoints
│   │   ├── auth.py            # /api/auth/signup, /login, /me, /logout
│   │   └── users.py           # /api/users CRUD endpoints
│   │
│   └── templates/             # Frontend HTML Pages
│       ├── home/
│       │   └── home.html      # Approvals modules dashboard
│       ├── module/
│       │   └── module.html    # Specific workflow module interface
│       ├── reset_password/
│       │   └── reset_password.html # Password reset page
│       ├── signin/
│       │   └── signin.html    # Sign in page
│       └── signup/
│           └── signup.html    # Sign up page with real-time validations
│
└── venv/                      # Python virtual environment
```

---

## ⚙️ Environment Configuration (`.env`)

Create or update the `.env` file in the project root directory:

```env
DATABASE_URL=postgresql://postgres:2002@localhost:5432/GPSL_workflow_DB
SECRET_KEY=gpsl_workflow_super_secret_session_key_2026_change_in_prod
APP_ENV=development
DEBUG=True
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

> **Psycopg 3 Driver Note**: The application automatically normalizes `postgresql://` into `postgresql+psycopg://` to utilize the modern `psycopg 3` binary driver.

---

## 🚀 Getting Started

### 1. Activate Virtual Environment

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.\venv\Scripts\activate.bat
```

### 2. Install Dependencies

```powershell
pip install fastapi uvicorn "psycopg[binary]" sqlalchemy pydantic pydantic-settings bcrypt python-dotenv jinja2
```

### 3. Run the Application

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🌐 Web Pages & Navigation

Once the server is running, access the web pages in your browser:

| Route | Page | Description |
|---|---|---|
| [`/`](http://127.0.0.1:8000/) | **Root Redirect** | Redirects to `/home` if authenticated, else `/signin`. |
| [`/signup`](http://127.0.0.1:8000/signup) | **Sign Up** | User registration with live password strength meter, phone parser, and direct link to sign in. |
| [`/signin`](http://127.0.0.1:8000/signin) | **Sign In** | Secure sign in with bcrypt verification, session cookie management, and link to sign up. |
| [`/home`](http://127.0.0.1:8000/home) | **Home Dashboard** | Workflow modules overview showing authenticated user name, email, job title, and sign out button. |
| [`/module`](http://127.0.0.1:8000/module) | **Module** | Specific approval workflow module interface. |
| [`/reset-password`](http://127.0.0.1:8000/reset-password) | **Reset Password** | Interface for resetting a forgotten password securely. |
| [`/docs`](http://127.0.0.1:8000/docs) | **API Swagger Docs** | Interactive OpenAPI / Swagger documentation for all endpoints. |

---

## 🔌 API Endpoints Reference

### 🔐 Authentication (`/api/auth`)

#### 1. Sign Up / Register
- **Endpoint**: `POST /api/auth/signup`
- **Payload**:
  ```json
  {
    "firstName": "Hansa",
    "lastName": "Lakshitha",
    "email": "hansa.demo@greenpower-sl.com",
    "phone": "+94 77 987 6543",
    "jobTitle": "Lead Project Manager",
    "password": "Password2026!#"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "requestId": "AR-2026-0005",
    "status": "active",
    "message": "Account created successfully!",
    "user": {
      "user_id": 5,
      "firstName": "Hansa Lakshitha",
      "email": "hansa.demo@greenpower-sl.com",
      "phone": [94, 77, 987, 6543],
      "jobTitle": "Lead Project Manager"
    }
  }
  ```

#### 2. Sign In
- **Endpoint**: `POST /api/auth/login`
- **Payload**:
  ```json
  {
    "email": "hansa.demo@greenpower-sl.com",
    "password": "Password2026!#",
    "remember": true
  }
  ```
- **Response** (`200 OK`): Sets HTTP-only session cookie and returns user profile.

#### 3. Current User Profile
- **Endpoint**: `GET /api/auth/me`
- **Headers**: Cookie session or `Authorization: Bearer <token>`
- **Response** (`200 OK`): Returns current user object.

#### 4. Sign Out
- **Endpoint**: `POST /api/auth/logout`
- **Response** (`200 OK`): Clears session cookie and returns `{ "redirectUrl": "/signin" }`.

---

### 🏥 System Health Check

- **Endpoint**: `GET /api/health`
- **Response**:
  ```json
  {
    "status": "healthy",
    "server": "online",
    "database": {
      "status": "connected",
      "engine": "PostgreSQL",
      "driver": "postgresql+psycopg",
      "database_name": "GPSL_workflow_DB",
      "host": "localhost",
      "port": 5432,
      "latency_ms": 1.2
    },
    "uptime_seconds": 240.5
  }
  ```

---

## 🔒 Security Highlights

1. **Password Hashing**: Bcrypt with automatic salting (12 rounds). Plaintext passwords are never stored in the database.
2. **Session Security**: Session tokens are cryptographically signed using HMAC-SHA256 with `SECRET_KEY` and transmitted via HTTP-only, SameSite cookies.
3. **Pydantic Validation**: All requests are strictly typed and sanitized before executing queries.
4. **SQL Injection Protection**: SQLAlchemy parameterized ORM queries prevent SQL injection vulnerabilities.
