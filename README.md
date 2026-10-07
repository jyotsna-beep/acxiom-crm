# AcxiomCRM

AcxiomCRM is a secure CRM assignment built with FastAPI, SQLAlchemy/Alembic, SQLite, React, Vite, Bootstrap, Axios, and React Router.

## Modules

Authentication and RBAC, Customers, Leads and conversion, Opportunities, Follow-Ups, Activities, User Management, Dashboard, Audit Logs, and scoped Reports.

Roles are Admin, Manager, and Sales Executive. Authorization is enforced by the API: Admin has full scope, Manager has own/direct-report scope, and Sales Executive has own/assigned scope.

## Setup

Prerequisites: Python 3.11+ and Node.js 18+.

Copy `.env.example` to `.env`. SQLite is the application database; set a long random `AUTH_SECRET_KEY` and keep `DATABASE_URL=sqlite:///./acxiomcrm.db`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python bootstrap_admin.py
uvicorn app.main:app --reload
```

Swagger: `http://localhost:8000/docs`.

```powershell
cd frontend
npm install
npm run dev
```

## Tests

```powershell
cd backend
python -m unittest discover -s tests -v
```

## Security

Passwords use Argon2 hashing and a complexity policy. Authentication uses short-lived HttpOnly cookies with CSRF protection, lockout tracking, token-version invalidation, server-side DTO validation, RBAC/record scoping, Alembic-managed schema, and append-oriented audit records. Passwords, hashes, tokens, and secrets are not exposed through APIs or audit metadata.
