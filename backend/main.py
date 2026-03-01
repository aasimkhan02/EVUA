import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import connect_db, close_db

# Add engine to path so benchmark routes can import pipeline modules
_ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="EVUA",
    description="AngularJS → Angular Migration Engine API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
from api.auth.routes import router as auth_router
from api.benchmarks.routes import router as benchmarks_router
from api.sessions.routes import router as sessions_router
from api.review.routes import router as review_router

app.include_router(auth_router, prefix="/api")
app.include_router(benchmarks_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(review_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "evua"}
