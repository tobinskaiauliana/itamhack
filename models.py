from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, ForeignKey, Text
from sqlalchemy.sql import func
from database import engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    username = Column(String)
    first_name = Column(String)
    created_at = Column(DateTime, server_default=func.now())

class TelegramCode(Base):
    __tablename__ = "telegram_codes"
    id = Column(Integer, primary_key=True)
    code = Column(String(6), unique=True)
    telegram_id = Column(BigInteger)
    telegram_username = Column(String)
    telegram_first_name = Column(String)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    def is_expired(self):
        if not self.expires_at:
            return True
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password_hash = Column(String)
    name = Column(String)
    role = Column(String, default="admin")
    created_at = Column(DateTime, server_default=func.now())

class Hackathon(Base):
    __tablename__ = "hackathons"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    date = Column(DateTime, nullable=False)
    team_size = Column(Integer, default=0)
    format = Column(String(20), nullable=False)
    photo_url = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey('admins.id'))
    created_at = Column(DateTime, server_default=func.now())

Base.metadata.create_all(bind=engine)