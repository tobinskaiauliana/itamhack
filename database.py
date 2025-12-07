import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from typing import Generator

DB_USER = os.getenv("DB_USER", "auth_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "auth_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "itamhack")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()