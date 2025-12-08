import random
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import TelegramCode, User, LanguageEnum, LevelEnum

class AuthService:
    @staticmethod
    def generate_code(length: int = 6) -> str:
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    @staticmethod
    def create_auth_code(
            db: Session,
            telegram_id: int,
            username: str = None,
            first_name: str = None
    ) -> TelegramCode:

        db.query(TelegramCode).filter(
            TelegramCode.telegram_id == telegram_id,
            TelegramCode.is_used == False
        ).delete(synchronize_session=False)

        code_str = AuthService.generate_code()
        # ИСПРАВЛЕНО: используем datetime.utcnow() вместо datetime.now(timezone.utc)
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        auth_code = TelegramCode(
            code=code_str,
            telegram_id=telegram_id,
            telegram_username=username,
            telegram_first_name=first_name,
            expires_at=expires_at,
            is_used=False
        )

        db.add(auth_code)
        db.commit()
        db.refresh(auth_code)

        return auth_code

    @staticmethod
    def verify_code(db: Session, code: str) -> dict:

        auth_code = db.query(TelegramCode).filter(
            TelegramCode.code == code,
            TelegramCode.is_used == False
        ).first()

        if not auth_code:
            return {"success": False, "error": "Код не найден"}

        if auth_code.is_expired():
            return {"success": False, "error": "Код истек"}

        user = db.query(User).filter(User.telegram_id == auth_code.telegram_id).first()

        if not user:
            user = User(
                telegram_id=auth_code.telegram_id,
                telegram_username=auth_code.telegram_username,
                name=auth_code.telegram_first_name,
                language=LanguageEnum.rus,
                level=LevelEnum.n
            )
            db.add(user)

        auth_code.is_used = True
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.telegram_username,
            "name": user.name,
            "photo_url": user.photo_url,
            "role": user.role,
            "language": user.language.value if user.language else "Русский",
            "level": user.level.value if user.level else "Новичок",
            "city": user.city,
            "university": user.university,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_telegram_id(db: Session, telegram_id: int) -> User:
        return db.query(User).filter(User.telegram_id == telegram_id).first()

    @staticmethod
    def update_user_profile(
            db: Session,
            user_id: int,
            name: str = None,
            role: str = None,
            language: str = None,
            level: str = None,
            city: str = None,
            university: str = None,
            about_text: str = None,
            skill1: str = None,
            skill2: str = None,
            skill3: str = None,
            skill4: str = None,
            skill5: str = None
    ) -> dict:
        user = AuthService.get_user_by_id(db, user_id)

        if not user:
            return {"success": False, "error": "Пользователь не найден"}

        if name is not None:
            user.name = name
        if role is not None:
            user.role = role
        if language is not None:
            try:
                user.language = LanguageEnum(language)
            except ValueError:
                return {"success": False, "error": "Некорректное значение языка"}
        if level is not None:
            try:
                user.level = LevelEnum(level)
            except ValueError:
                return {"success": False, "error": "Некорректное значение уровня"}
        if city is not None:
            user.city = city
        if university is not None:
            user.university = university
        if about_text is not None:
            user.about_text = about_text
        if skill1 is not None:
            user.skill1 = skill1
        if skill2 is not None:
            user.skill2 = skill2
        if skill3 is not None:
            user.skill3 = skill3
        if skill4 is not None:
            user.skill4 = skill4
        if skill5 is not None:
            user.skill5 = skill5

        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "message": "Профиль обновлен",
            "user": {
                "id": user.id,
                "name": user.name,
                "role": user.role,
                "language": user.language.value if user.language else None,
                "level": user.level.value if user.level else None,
                "city": user.city,
                "university": user.university,
                "about_text": user.about_text,
                "skill1": user.skill1,
                "skill2": user.skill2,
                "skill3": user.skill3,
                "skill4": user.skill4,
                "skill5": user.skill5
            }
        }

    @staticmethod
    def update_user_photo(db: Session, user_id: int, photo_url: str) -> dict:
        user = AuthService.get_user_by_id(db, user_id)

        if not user:
            return {"success": False, "error": "Пользователь не найден"}

        user.photo_url = photo_url
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "message": "Фото обновлено",
            "photo_url": user.photo_url
        }