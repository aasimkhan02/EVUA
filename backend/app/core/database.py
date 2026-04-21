from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

# For SQLite, we need to allow multithreading access
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL, 
    echo=True, 
    connect_args=connect_args
)

def init_db():
    # This will create tables if they don't exist
    # In production, you'd use Alembic
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
