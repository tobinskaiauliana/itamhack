from database import SessionLocal
from models import Admin
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

email = input("Email админа: ").strip()
name = input("Имя админа: ").strip()
password = input("Пароль: ").strip()

password_hash = pwd_context.hash(password)

db = SessionLocal()
try:
    admin = Admin(email=email, password_hash=password_hash, name=name)
    db.add(admin)
    db.commit()
    print(f"Админ {email} создан")
except Exception as e:
    print(f"Ошибка: {e}")
finally:
    db.close()