from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import migration

app = FastAPI()

# CORS (IMPORTANT for React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict to localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(migration.router, prefix="/api")

@app.get("/")
def root():
    return {"status": "EVUA backend running"}