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
POST /companies/
Required header: `Authorization: Bearer <token>`
```json
{
  "name": "My Company",
  "description": "Company description",
  "is_visible": true
}
```

### Get all companies (with pagination)
GET /companies/?page=1&page_size=10

Returns only visible (`is_visible=true`) companies.

### Get company by ID
GET /companies/{company_id}

### Update company
PATCH /companies/{company_id}
Required header: `Authorization: Bearer <token>`
Access: Available only to the company Owner.
Request Body: Send only the fields that need to be updated.
```json
{
  "name": "Updated name"
}
```

### Delete company
DELETE /companies/{company_id}
Required header: `Authorization: Bearer <token>`
Access: Available only to the company Owner.

## Tests

```bash
python -m pytest tests/ -v
```