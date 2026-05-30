import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Додаємо блок CORS для роботи з фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Дозволяємо запити з будь-яких адрес
    allow_credentials=True,
    allow_methods=["*"],  # Дозволяємо всі методи (GET, POST тощо)
    allow_headers=["*"],  # Дозволяємо всі заголовки
)
@app.get("/")
def health_check():
    return {
        "status_code": 200,
        "detail": "ok",
        "result": "working"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)