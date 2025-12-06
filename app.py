from fastapi import FastAPI, HTTPException, Query, Depends, Header, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import bcrypt
import jwt
import os
import secrets
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from typing import Optional
import shutil
from database import get_db
from models import User, Admin, Hackathon
from auth_service import AuthService

app = FastAPI()

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

if not os.path.exists("jwt_secret.txt"):
    with open("jwt_secret.txt", "w") as f:
        f.write(secrets.token_hex(32))

with open("jwt_secret.txt", "r") as f:
    JWT_SECRET = f.read().strip()

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 10

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    language: Optional[str] = None
    level: Optional[str] = None
    city: Optional[str] = None
    university: Optional[str] = None


def create_admin_token(admin_id: int, email: str, name: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(admin_id),
        "email": email,
        "name": name,
        "role": role,
        "type": "admin",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_admin_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "admin":
            raise HTTPException(status_code=401, detail="Неверный тип токена")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Токен истек")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Неверный токен")

async def get_current_admin(
        authorization: str = Header(None),
        db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    token = authorization.replace("Bearer ", "")
    payload = verify_admin_token(token)
    admin_id = int(payload.get("sub"))

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Админ не найден")

    return admin

#-------------------------------------

#Авторизация участника через тг
@app.get("/auth/telegram")
def login_participant(code: str = Query(...), db: Session = Depends(get_db)):
    result = AuthService.verify_code(db, code)
    if not result["success"]:
        raise HTTPException(400, result["error"])
    return result

#Добавление инфы на акк
@app.put("/api/users/me")
def update_my_profile(
        request: UpdateProfileRequest,
        user_id: int = Query(...),
        db: Session = Depends(get_db)
):
    result = AuthService.update_user_profile(
        db=db,
        user_id=user_id,
        name=request.name,
        role=request.role,
        language=request.language,
        level=request.level,
        city=request.city,
        university=request.university
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


#Данные в профиле
@app.get("/users/me")
def get_my_profile(user_id: int = Query(...), db: Session = Depends(get_db)):
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.telegram_username,
        "name": user.name,
        "photo_url": user.photo_url,
        "role": user.role,
        "language": user.language.value if user.language else None,
        "level": user.level.value if user.level else None,
        "city": user.city,
        "university": user.university,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }


# Загрузить фото профиля
@app.post("/users/me/photo")
async def upload_profile_photo(
        photo: UploadFile = File(...),
        user_id: int = Query(...),
        db: Session = Depends(get_db)
):
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    file_ext = os.path.splitext(photo.filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, detail="Неподдерживаемый формат файла")

    photo.file.seek(0, 2)
    file_size = photo.file.tell()
    photo.file.seek(0)

    if file_size > 5 * 1024 * 1024:
        raise HTTPException(400, detail="Файл слишком большой (максимально 5МБ)")

    filename = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    user.photo_url = f"/uploads/{filename}"
    db.commit()

    return {
        "success": True,
        "message": "Фото загружено",
        "photo_url": user.photo_url
    }

#Вход админа
@app.post("/admin/login")
def login_admin(request: AdminLoginRequest, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == request.email).first()

    if not admin or not bcrypt.checkpw(request.password.encode(), admin.password_hash.encode()):
        raise HTTPException(401, "Неверный email или пароль")

    token = create_admin_token(
        admin_id=admin.id,
        email=admin.email,
        name=admin.name,
        role=admin.role
    )

    return {
        "success": True,
        "token": token,
        "admin": {
            "id": admin.id,
            "email": admin.email,
            "name": admin.name
        }
    }

# Создать хакатон
@app.post("/admin/hackathons")
async def create_hackathon(
title: str = Form(...),
        description: str = Form(""),
        date: float = Form(...),
        team_size: int = Form(...),
        format: str = Form(...),
        registration: Optional[float] = Form(None),
        photo: Optional[UploadFile] = File(None),
        current_admin: Admin = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    photo_url = None

    if photo:
        ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        file_ext = os.path.splitext(photo.filename.lower())[1]
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, detail="Неподдерживаемый формат файла")

        photo.file.seek(0, 2)
        file_size = photo.file.tell()
        photo.file.seek(0)

        if file_size > 5 * 1024 * 1024:
            raise HTTPException(400, detail="Файл слишком большой (максимально 5МБ)")

        filename = f"hackathon_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

        photo_url = f"/uploads/{filename}"

    db_hackathon = Hackathon(
        title=title,
        description=description,
        date=date,
        registration_deadline=registration,
        team_size=team_size,
        format=format,
        created_by=current_admin.id,
        photo_url=photo_url
    )

    db.add(db_hackathon)
    db.commit()
    db.refresh(db_hackathon)

    return {
        "success": True,
        "message": "Хакатон успешно создан",
        "hackathon": {
            "id": db_hackathon.id,
            "title": db_hackathon.title,
            "description": db_hackathon.description,
            "date": db_hackathon.date,
            "team_size": db_hackathon.team_size,
            "format": db_hackathon.format,
            "registration": db_hackathon.registration_deadline,
            "photo_url": photo_url,
            "created_at": db_hackathon.created_at.isoformat()
        }
    }

# Удалить хакатон
@app.delete("/admin/hackathons/{hackathon_id}")
def delete_hackathon(
        hackathon_id: int,
        current_admin: Admin = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()

    if not hackathon:
        raise HTTPException(404, detail="Хакатон не найден")

    if hackathon.created_by != current_admin.id and current_admin.role != "superadmin":
        raise HTTPException(403, detail="Недостаточно прав")

    if hackathon.photo_url:
        filename = hackathon.photo_url.split("/")[-1]
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.delete(hackathon)
    db.commit()

    return {
        "success": True,
        "id": hackathon_id,
        "message": "Хакатон удален"
    }

# Получить все хакатоны
@app.get("/hackathons")
def get_all_hackathons(db: Session = Depends(get_db)):
    hackathons = db.query(Hackathon).order_by(Hackathon.date.desc()).all()

    hackathons_list = []
    for h in hackathons:
        hackathons_list.append({
            "id": h.id,
            "title": h.title,
            "format": h.format,
            "team_size": h.team_size,
            "date": h.date,
            "imageUrl": h.photo_url,
            "description": h.description,
            "registration": h.registration_deadline
        })

    return {
        "hackathons": hackathons_list,
        "total": len(hackathons_list)
    }

# Получить один хакатон
@app.get("/hackathons/{hackathon_id}")
def get_hackathon(hackathon_id: int, db: Session = Depends(get_db)):
    hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()

    if not hackathon:
        raise HTTPException(404, detail="Хакатон не найден")

    admin = db.query(Admin).filter(Admin.id == hackathon.created_by).first()

    return {
        "id": hackathon.id,
        "title": hackathon.title,
        "team_size": hackathon.team_size,
        "date": hackathon.date,
        "registration": hackathon.registration_deadline,
        "format": hackathon.format,
        "description": hackathon.description,
        "imageUrl": hackathon.photo_url
    }

#Статистика (админ)
@app.get("/admin/stats")
def get_stats(
        current_admin: Admin = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    return {
        "users": db.query(User).count(),
        "hackathons": db.query(Hackathon).count(),
        "your_hackathons": db.query(Hackathon).filter(Hackathon.created_by == current_admin.id).count()
    }