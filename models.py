from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, ForeignKey, Text, Float, Enum
from sqlalchemy.sql import func
from database import engine
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()

class LanguageEnum(str, enum.Enum):
    rus = "Русский"
    eng = "Английский"
    both = "Русский/Английский"

class LevelEnum(str, enum.Enum):
    n = "Новичок"
    o = "Опытный"
    p = "Про"

#--------таблицы
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    photo_url = Column(String, nullable=True)
    telegram_username = Column(String, nullable=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=True)
    language = Column(Enum(LanguageEnum), nullable=True, default=LanguageEnum.rus)
    level = Column(Enum(LevelEnum), nullable=True, default=LevelEnum.n)
    city = Column(String, nullable=True)
    university = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


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
        now_utc = datetime.now(timezone.utc)
        if self.expires_at.tzinfo is None:
            expires_at_utc = self.expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at_utc = self.expires_at.astimezone(timezone.utc)
        return now_utc > expires_at_utc

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
    date = Column(Float, nullable=False)
    registration_deadline = Column(Float, nullable=True)
    team_size = Column(Integer, default=0)
    format = Column(String(20), nullable=False)
    photo_url = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey('admins.id'))
    created_at = Column(DateTime, server_default=func.now())

Base.metadata.create_all(bind=engine)