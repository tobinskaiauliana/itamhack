from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, ForeignKey, Text, Float, Enum
from sqlalchemy.sql import func
from database import Base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime


class LanguageEnum(str, enum.Enum):
    rus = "Русский"
    eng = "Английский"
    both = "Русский/Английский"


class LevelEnum(str, enum.Enum):
    n = "Новичок"
    o = "Опытный"
    p = "Про"


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
    about_text = Column(Text, nullable=True)
    skill1 = Column(String, nullable=True)
    skill2 = Column(String, nullable=True)
    skill3 = Column(String, nullable=True)
    skill4 = Column(String, nullable=True)
    skill5 = Column(String, nullable=True)
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
        """Проверка истечения срока кода"""
        if not self.expires_at:
            return True
        # Простая проверка - сравниваем с текущим UTC временем
        return datetime.utcnow() > self.expires_at


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
    date = Column(String, nullable=False)
    registration_deadline = Column(String, nullable=True)
    team_size = Column(Integer, default=0)
    format = Column(String(20), nullable=False)
    photo_url = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey('admins.id'))
    created_at = Column(DateTime, server_default=func.now())
    admin = relationship("Admin")


class TeammateRequest(Base):
    __tablename__ = "teammate_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")


class TeamRequest(Base):
    __tablename__ = "team_requests"
    id = Column(Integer, primary_key=True)
    hackathon_id = Column(Integer, ForeignKey('hackathons.id'), nullable=False)
    team_name = Column(String(200), nullable=False)
    team_photo_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    hackathon = relationship("Hackathon")
    creator = relationship("User")


class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(Integer, primary_key=True)
    team_request_id = Column(Integer, ForeignKey('team_requests.id'), nullable=False)
    full_name = Column(String(200), nullable=False)
    telegram_username = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    university = Column(String(200), nullable=True)
    position = Column(Integer, nullable=False)

    team_request = relationship("TeamRequest")