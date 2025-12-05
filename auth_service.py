import random
import string
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from models import TelegramCode, User

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
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

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
                username=auth_code.telegram_username,
                first_name=auth_code.telegram_first_name
            )
            db.add(user)

        auth_code.is_used = True
        db.commit()

        return {
            "success": True,
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name
        }

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        return db.query(User).filter(User.id == user_id).first()