from data.core.database import Base, engine, DB_PATH
import os

print(f"Applying database schema updates to {DB_PATH} directly...")
Base.metadata.create_all(bind=engine)
print("Done!")
