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
- Analytics (User rating, per-quiz weekly averages, last attempts, company-wide member analytics for Owners/Admins)


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


## Data Export (Task BE #14)

Users can export their own quiz results, and company Owners/Admins can export
results for their company (all members or a specific one), in either JSON or CSV format.
Data is read directly from the Redis cache described in Task BE #13.

All endpoints require:
```http
Authorization: Bearer <token>
```

### Export My Own Results
GET /quiz-results/me/export?export_format=json

Query parameters:
- `export_format` — `json` (default) or `csv`
- `company_id` — optional, filter by a specific company
- `quiz_id` — optional, filter by a specific quiz

Returns only the results of the currently authenticated user.

### Export Company Results
GET /quiz-results/companies/{company_id}/export?export_format=csv

Query parameters:
- `export_format` — `json` (default) or `csv`
- `user_id` — optional, export results of a specific company member (Owner/Admin only)
- `quiz_id` — optional, filter by a specific quiz

Access: Owner or Admin of the company only. Returns 404 if the company or the
specified `user_id` (as a member) does not exist, and 403 if the requester
lacks Owner/Admin permissions.

### CSV Format
When `export_format=csv`, the response is returned as a downloadable file
(`Content-Disposition: attachment`) with the following columns:


## Analytics (Task BE #15)

Provides performance analytics for quiz results — both for individual users
(their own overall rating, per-quiz weekly averages, and last attempts) and
for company Owners/Admins (aggregated stats across all company members).

Averages are calculated as a **weighted average**
(`SUM(correct_answers) / SUM(total_questions)`), not a simple average of
per-quiz percentages, so quizzes with more questions are weighted
proportionally to their size. Weekly breakdowns use PostgreSQL's
`date_trunc('week', ...)` to group results by calendar week.

All endpoints require:
```http
Authorization: Bearer <token>
```

### My Overall Rating
GET /analytics/me/rating

Returns the current user's overall average score across all quizzes in all
companies they belong to.

Response:
```json
{
  "overall_average": 87.5
}
```

### My Quiz Averages (Weekly)
GET /analytics/me/quizzes/{quiz_id}

Returns the current user's average score for a specific quiz, broken down
by week. Returns 404 if the quiz does not exist.

Response:
```json
{
  "quiz_id": "uuid",
  "quiz_title": "Python Basics",
  "weekly_scores": [
    {"week_start": "2026-06-29", "average_score": 100.0},
    {"week_start": "2026-07-13", "average_score": 50.0}
  ]
}
```

### My Last Attempts
GET /analytics/me/last-attempts

Returns a list of quizzes the current user has taken, along with the
timestamp of their last completion for each.

Response:
```json
[
  {
    "quiz_id": "uuid",
    "quiz_title": "Python Basics",
    "last_completed_at": "2026-07-17"
  }
]
```

### Company Members' Averages (Weekly)
GET /analytics/companies/{company_id}/members

Access: Owner or Admin of the company only. Returns the weekly average
scores of every member in the company. Returns 404 if the company does
not exist, and 403 if the requester is not an Owner/Admin.

Response:
```json
[
  {
    "user_id": "uuid",
    "weekly_scores": [
      {"week_start": "2026-06-29", "average_score": 100.0}
    ]
  }
]
```

### Company Member's Quiz Averages
GET /analytics/companies/{company_id}/members/{user_id}

Access: Owner or Admin of the company only. Returns a detailed, per-quiz
weekly breakdown for a specific company member.

Response:
```json
[
  {
    "quiz_id": "uuid",
    "quiz_title": "SQL Advanced",
    "weekly_scores": [
      {"week_start": "2026-06-29", "average_score": 60.0}
    ]
  }
]
```

### Company Members' Last Attempts
GET /analytics/companies/{company_id}/last-attempts

Access: Owner or Admin of the company only. Returns a list of all company
members along with the timestamp of their most recent quiz attempt
(across any quiz in the company).

Response:
```json
[
  {
    "user_id": "uuid",
    "last_completed_at": "2026-07-17"
  }
]
```


## Notifications (Task BE #16)

Company members are automatically notified when a new quiz is created in
their company. Users can view their own notifications (paginated) and mark
them as read.

Recipients are resolved via a lightweight query (only `user_id`s, no full
`User` objects), and all notifications are inserted in a single batch to
avoid N+1 queries.

All endpoints require:
```http
Authorization: Bearer <token>
```

- `GET /notifications/?page=1&per_page=10` — paginated list, most recent first
- `PATCH /notifications/{notification_id}/read` — mark as read (404 if not found, 403 if not owner)

### Migration
```bash
alembic upgrade head
```


## Scheduled Reminders (Task BE #17)

A background job checks daily whether users have completed all available
quizzes in their companies within the last 24 hours, and sends a reminder
notification (via the system from Task BE #16) for each missed quiz.

- **Scheduler**: APScheduler (`AsyncIOScheduler`), chosen over Celery since
  it needs no separate broker or worker process and integrates directly
  into the FastAPI `lifespan`.
- **Schedule**: runs daily at `00:00 UTC`.
- **Query**: a single LEFT JOIN query finds all users missing a `QuizResult`
  for an available quiz in the last 24 hours — no per-user queries.
- **Notifications**: all reminders for a run are inserted in a single
  batch (`create_many`) to avoid N+1 inserts.

### Migration

`QuizResult.completed_at` was changed to a timezone-aware column
(`TIMESTAMPTZ`) so comparisons with the current UTC time are accurate:
```bash
alembic upgrade head
```


## Testing

Tests are split into two categories:

- `tests/unit/` — unit tests for the service layer, using `AsyncMock` instead of a real database. Fast, no DB/Redis required.
- `tests/integration/` — integration tests against real HTTP endpoints (e.g. health check). Requires the app running with DB and Redis connected.

### Run all tests
```bash
pytest
```

### Run only unit tests
```bash
pytest tests/unit
```

### Run only integration tests
```bash
pytest tests/integration
```


## AWS Infrastructure (BE #19)

The project is deployed on AWS with two managed databases, in preparation for production deployment.

### PostgreSQL — Amazon RDS
- **Instance:** db.t4g.micro (Free tier)
- **Engine:** PostgreSQL 18.3
- **Region:** eu-west-1 (Ireland)
- **Public access:** Yes (temporary, for local development)
- **Security group:** internship-postgres-sg — allows inbound traffic on port 5432 from an allowed IP address

### Redis — Amazon ElastiCache
- **Node type:** cache.t4g.micro (Free tier)
- **Cluster mode:** Disabled (1 shard, 0 replicas)
- **Region:** eu-west-1 (Ireland)
- **Encryption in transit:** Required (TLS)
- **Security group:** internship-postgres-sg — allows inbound traffic on port 6379

 **Note:** ElastiCache does not support public access. It will only become reachable once the application is deployed inside VPC

### Environment variables
See `.env.sample` for the full list of required variables (POSTGRES_*, REDIS_*).


## Deployment (BE #20)

The application is deployed on **AWS EC2** (Ubuntu 24.04, `t3.micro`, `eu-west-1`),
alongside RDS PostgreSQL (`db.t4g.micro`) and ElastiCache Redis (`cache.t4g.micro`,
TLS required), all in the same VPC.

**Note on approach:** AWS App Runner was initially attempted but returned a
`SubscriptionRequiredException` (account-level issue, unrelated to region or
IAM permissions). EC2 was used instead, consistent with the approach discussed
in the group chat.

### CI/CD

GitHub Actions (`.github/workflows/deploy.yml`) triggers on push to `develop`.
Each run:
1. Temporarily opens SSH (port 22) in the EC2 Security Group for the
   runner's IP only
2. Connects via SSH, runs `git pull`, rebuilds the Docker image, and
   restarts the container
3. Revokes the SSH rule afterward (`if: always()`), regardless of outcome

### Access

Swagger UI: `http://18.201.205.195:8000/docs`