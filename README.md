# Internship Backend

FastAPI backend application.

## Requirements

- Python 3.13+
- FastAPI 0.136.3 
- Uvicorn 0.48.0 
- Pytest 9.0.3
- Docker & Docker Compose
- Database: PostgreSQL 15 (Alpine)
- ORM / Driver: SQLAlchemy + Asyncpg (Fully asynchronous database connection)
- Caching / Task Queue: Redis 7 (Alpine) + redis.asyncio

## Setup

1. Clone the repository:
```bash
   git clone https://github.com/Vitalii-48/back-end.git
   cd internship-backend
```

2. Create virtual environment:
```bash
   python -m venv .venv
```

3. Activate virtual environment:
```bash
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
```

4. Install dependencies:
```bash
   pip install -r requirements.txt
```

5. Create `.env` file from sample:
# Windows (cmd/PowerShell)
```bash
   copy .env.sample .env
```
# Linux/Mac
```bash
   cp .env.sample .env
```


## Running the Application

### Locally
```bash
uvicorn main:app --reload
```
- App: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

### Docker
```bash
docker compose up --build
```

Stop:
```bash
docker compose down
```

## Database Migrations (Alembic)
Before running the app or after modifying database models, apply migrations:

# Apply migrations to the database
```bash
  alembic upgrade head
```

# Create a new automatic migration (if you changed models)
```bash
  alembic revision --autogenerate -m "migration_name"
```

## Docker Deployment

Build and Run the Containers
```bash
  docker compose up --build
```

Run container:
```bash
docker run -p 8000:8000 --name fastapi-app internship-backend
```

Stop the Containers
```bash
  docker compose down
```

## API Endpoints

- Health check (PostgreSQL + Redis status)
- Auth (signin,signup)
- Users(Get all users, Create a new user, Get user by ID, Update user, Delete user)
- Companies (Create company, Get all companies with pagination, Get company by ID, Update company, Delete company)
- Company Actions & Admins** (Invitations, Join Requests, Member & Admin role management)

## Authentication (Авторизація)

### Login/Password
POST /auth/signin
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```
Returns a JWT token.

### Auth0
POST /auth/auth0
```json
{
  "token": "your_auth0_token"
}
```
Get Auth0 token: https://romanxeo.github.io/internship-token/

### Get current user
GET /me
Required header: `Authorization: Bearer <token>`


## Companies (Компанії)

Any authenticated user can create a company and automatically becomes its Owner.
### Create company
POST /company/
Required header: `Authorization: Bearer <token>`
```json
{
  "name": "My Company",
  "description": "Company description",
  "is_visible": true
}
```

### Get all companies (with pagination)
GET /company/?page=1&page_size=10

Returns only visible (`is_visible=true`) companies.

### Get company by ID
GET /company/{company_id}

### Update company
PATCH /company/{company_id}
Required header: `Authorization: Bearer <token>`
Access: Available only to the company Owner.
Request Body: Send only the fields that need to be updated.
```json
{
  "name": "Updated name"
}
```

### Delete company
DELETE /company/{company_id}
Required header: `Authorization: Bearer <token>`
Access: Available only to the company Owner.



## Company Actions

All endpoints below require:

```http
Authorization: Bearer <token>
```

### Invitations

#### Send invitation

Owner sends an invitation to a user:
POST /company/{company_id}/invitations
```json
{
  "user_id": "user-uuid"
}
```

Owner views sent pending invitations:
GET /company/{company_id}/invitations?page=1&per_page=10

Owner cancels an invitation:
POST /company/invitations/{request_id}/cancel

User views received invitations:
GET /company/me/invitations?page=1&per_page=10

User accepts an invitation:
POST /company/invitations/{request_id}/accept

User declines an invitation:
POST /company/invitations/{request_id}/decline

### Join Requests

User requests to join a company:
POST /company/{company_id}/join-requests

User views own pending join requests:
GET /company/me/join-requests?page=1&per_page=10

User cancels own join request:
POST /company/join-requests/{request_id}/cancel

Owner views pending join requests:
GET /company/{company_id}/join-requests?page=1&per_page=10

Owner accepts a join request:
POST /company/join-requests/{request_id}/accept

Owner declines a join request:
POST /company/join-requests/{request_id}/decline

### Members

View company members:
GET /company/{company_id}/members?page=1&per_page=10

User leaves company:
DELETE /company/{company_id}/members/me

Owner removes a member:
DELETE /company/{company_id}/members/{user_id}


## Company Actions & Administration
All endpoints listed below require a valid bearer token passed via headers: Authorization: Bearer <token>.

### 📩 Invitations Workflow
Owner sends an invitation to a user:
POST /company/{company_id}/invitations (Body: {"user_id": "uuid"})

Owner views sent pending invitations:
GET /company/{company_id}/invitations?page=1&per_page=10

Owner cancels an invitation:
POST /company/invitations/{request_id}/cancel

User views received invitations:
GET /company/me/invitations?page=1&per_page=10

User accepts an invitation:
POST /company/invitations/{request_id}/accept

User declines an invitation:
POST /company/invitations/{request_id}/decline

### 📥 Join Requests Workflow
User requests to join a company:
POST /company/{company_id}/join-requests

User views own pending join requests:
GET /company/me/join-requests?page=1&per_page=10

User cancels own join request:
POST /company/join-requests/{request_id}/cancel

Owner views pending join requests:
GET /company/{company_id}/join-requests?page=1&per_page=10

Owner accepts a join request:
POST /company/join-requests/{request_id}/accept

Owner declines a join request:
POST /company/join-requests/{request_id}/decline

### 👥 Members & Administrative Management
This module handles role-based access control inside companies, distinguishing permissions between Owners, Admins
and Members.

Method/Endpoint - DescriptionAccess -> Level
GET/company/{company_id}/members - Get paginated list of all members (total count included) -> Member / Admin / Owner

DELETE/company/{company_id}/members/me - Leave the company (Owners cannot leave their own company) -> Member / Admin

DELETE/company/{company_id}/members/{user_id} - Remove a member from the company -> Owner Only

POST/company/{company_id}/admins/{user_id} - Promote a member to Administrator role -> Owner Only

POST/company/{company_id}/admins/{user_id} - Demote an Administrator back to standard Member -> Owner Only

GET/company/{company_id}/admins - Get paginated list of active company administrators -> Member / Admin / Owner

Example Members/Admins Paginated Response:JSON{
  "members": [
    {
      "id": "c3098f41-0731-419b-a36c-2f9543e06de9",
      "company_id": "8fa11b22-54a7-4b72-8802-95f329938e11",
      "user_id": "1fa54f11-92e1-4c32-b715-1a953e9982fb",
      "role": "ADMIN",
      "created_at": "2026-06-23T12:00:00Z"
    }
  ],
  "total": 1
}



## Quiz Workflow

All endpoints require:
```http
Authorization: Bearer <token>
```

### Submit Quiz
POST /companies/{company_id}/quiz-workflow/{quiz_id}/submit

Submit answers for a quiz. User must be a member of the company.
```json
{
  "answers": [
    {
      "question_id": "uuid",
      "selected_option_ids": ["uuid"]
    }
  ]
}
```

### Get My Average Score in Company
GET /companies/{company_id}/quiz-workflow/my-average-score

Returns the current user's average score within the specified company.

### Get Member's Average Score
GET /companies/{company_id}/quiz-workflow/members/{user_id}/average-score

Returns average score of a specific member. Available to Owner/Admin or the user themselves.


## Redis Temporary Caching (Task BE #13)
To ensure secure high-performance data processing and transient tracking,
detailed quiz interactions are cached temporarily using Redis.

- Lifespan Context Manager: Connection pools open on app startup and execute clean shutdown steps (aclose()) 
  when Uvicorn processes exit.

- TTL Constraint: Individual question selection models, metadata states,
  and correct-flag evaluations are compiled into JSON payloads
  and held under Redis set(ex=...) for exactly 48 hours before auto-deletion.

- Structure Pattern: Keys use string schemas (quiz_attempt:{user_id}:{company_id}:{quiz_id}:{timestamp})
  enabling pattern matching scans via Redis keys() streams.


## Tests

```bash
python -m pytest tests/ -v
```