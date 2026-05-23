from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db

app = FastAPI(title="BreakoutStocks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok"}
