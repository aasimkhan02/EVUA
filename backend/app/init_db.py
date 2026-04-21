from app.core.database import init_db
from app.models.database_models import * # Import models to ensure they are registered with SQLModel

if __name__ == "__main__":
    print("Initializing EVUA Database...")
    init_db()
    print("Database structures created successfully.")
