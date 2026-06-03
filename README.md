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

Local Development (Windows / Linux / Mac)
To run the Uvicorn development server locally:

```bash
uvicorn main:app --reload
```

Application runs on `http://127.0.0.1:8000`
Interactive API documentation (Swagger UI): http://127.0.0.1:8000/docs


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

## Tests

```bash
python -m pytest tests/ -v
```