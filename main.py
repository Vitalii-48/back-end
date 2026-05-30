import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def health_check():
    return {
        "status_code": 200,
        "detail": "ok",
        "result": "working"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)