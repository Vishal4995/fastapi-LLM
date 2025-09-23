# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# optional: load from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://fastapi:fastapi@localhost:5432/fastapi"  # fallback
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,          # healthier connections
    connect_args={} if DATABASE_URL.startswith("postgresql") else {"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
