from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import migration, auth, projects
from app.core.database import init_db

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()

# CORS (Permissive for Demo/College Project)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "healthy", "service": "EVUA Backend"}

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(migration.router, prefix="/api")

@app.get("/")
def root():
    return {"status": "EVUA backend running"}