# Internship Backend

FastAPI backend application.

## Requirements

- Python 3.13+
- FastAPI 0.136.3 
- Uvicorn 0.48.0 
- Pytest 9.0.3
- Docker
- Database: PostgreSQL 15 (Alpine)
- ORM / Driver: SQLAlchemy + Asyncpg (Fully asynchronous database connection)
- Caching / Task Queue: Redis 7 (Alpine) + redis.asyncio
- Containerization: Docker & Docker Compose

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
```bash
   cp .env.sample .env
```


## Run the Uvicorn development server

```bash
uvicorn main:app --reload
```

Application runs on `http://127.0.0.1:8000`

## Docker

Build image
```bash
docker build -t internship-backend .
```

Run container:
```bash
docker run -p 8000:8000 --name fastapi-app internship-backend
```

Build and Run the Containers
```bash
docker-compose up --build
```

## Tests

```bash
python -m pytest tests/ -v
```