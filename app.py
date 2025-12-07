from fastapi import FastAPI, HTTPException, Query, Depends, Header, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import bcrypt
import jwt
import os
import secrets
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from typing import Optional, List
import shutil
from database import get_db
from models import User, Admin, Hackathon, TeammateRequest, TeamRequest, TeamMember
from auth_service import AuthService
import asyncio
from bot import send_telegram_notification

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
    about_text: Optional[str] = None
    skill1: Optional[str] = None
    skill2: Optional[str] = None
    skill3: Optional[str] = None
    skill4: Optional[str] = None
    skill5: Optional[str] = None

class CreateTeammateRequest(BaseModel):
    description: Optional[str] = None

class TeamMemberRequest(BaseModel):
    full_name: str
    telegram_username: str
    role: str
    university: Optional[str] = None

class CreateTeamRequest(BaseModel):
    team_name: str
    description: Optional[str] = None
    members: List[TeamMemberRequest]


class LikeTeamRequest(BaseModel):
    team_request_id: int
    action: str

class TeammateProfileResponse(BaseModel):
    id: int
    user_id: int
    name: str
    telegram_username: Optional[str] = None
    photo_url: Optional[str] = None
    role: Optional[str] = None
    level: Optional[str] = None
    language: Optional[str] = None
    city: Optional[str] = None
    university: Optional[str] = None
    about_text: Optional[str] = None
    created_at: Optional[str] = None

class TeammateLikeRequest(BaseModel):
    teammate_id: int
    action: str

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


# -------------------------------------

# Авторизация участника через тг
@app.get("/auth/telegram")
def login_participant(code: str = Query(...), db: Session = Depends(get_db)):
    result = AuthService.verify_code(db, code)
    if not result["success"]:
        raise HTTPException(400, result["error"])
    return result


# Добавление инфы на акк
@app.put("/users/me")
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
        university=request.university,
        about_text=request.about_text,
        skill1=request.skill1,
        skill2=request.skill2,
        skill3=request.skill3,
        skill4=request.skill4,
        skill5=request.skill5
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# Данные в профиле
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
        "about_text": user.about_text,
        "skill1": user.skill1,
        "skill2": user.skill2,
        "skill3": user.skill3,
        "skill4": user.skill4,
        "skill5": user.skill5,
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

#Получение команд пользователя
@app.get("/users/me/teams")
def get_my_teams(
        user_id: int = Query(...),
        db: Session = Depends(get_db)
):
    created_teams = db.query(TeamRequest).filter(
        TeamRequest.created_by == user_id,
        TeamRequest.is_active == True
    ).all()
    member_teams = db.query(TeamRequest).join(
        TeamMember, TeamRequest.id == TeamMember.team_request_id
    ).filter(
        TeamMember.telegram_username == User.telegram_username,
        TeamRequest.is_active == True
    ).all()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    if user.telegram_username:
        member_teams = db.query(TeamRequest).join(
            TeamMember, TeamRequest.id == TeamMember.team_request_id
        ).filter(
            TeamMember.telegram_username == user.telegram_username,
            TeamRequest.is_active == True
        ).all()
    else:
        member_teams = []
    all_teams = created_teams + member_teams
    unique_teams = {team.id: team for team in all_teams}.values()

    teams_list = []
    for team in unique_teams:
        members = db.query(TeamMember).filter(
            TeamMember.team_request_id == team.id
        ).all()
        hackathon = db.query(Hackathon).filter(Hackathon.id == team.hackathon_id).first()

        teams_list.append({
            "id": team.id,
            "team_name": team.team_name,
            "description": team.description,
            "team_photo_url": team.team_photo_url,
            "hackathon": {
                "id": hackathon.id if hackathon else None,
                "title": hackathon.title if hackathon else None,
                "date": hackathon.date if hackathon else None
            },
            "members": [
                {
                    "full_name": m.full_name,
                    "telegram_username": m.telegram_username,
                    "role": m.role,
                    "university": m.university,
                    "position": m.position
                }
                for m in members
            ],
            "is_creator": team.created_by == user_id,
            "created_at": team.created_at.isoformat() if team.created_at else None
        })

    return {
        "success": True,
        "teams": teams_list,
        "total": len(teams_list),
        "created_count": len(created_teams),
        "member_count": len(member_teams)
    }
# Вход админа
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
        date: str = Form(...),
        team_size: int = Form(...),
        format: str = Form(...),
        registration: Optional[str] = Form(None),
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


# Статистика (админ)
@app.get("/admin/stats")
def get_stats(
        current_admin: Admin = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    total_hackathons = db.query(Hackathon).count()
    total_users = db.query(User).count()
    all_hackathons = db.query(Hackathon).order_by(desc(Hackathon.created_at)).all()

    hackathons_list = []
    for hackathon in all_hackathons:
        teams_count = db.query(TeamRequest).filter(
            TeamRequest.hackathon_id == hackathon.id,
            TeamRequest.is_active == True
        ).count()

        hackathons_list.append({
            "title": hackathon.title,
            "format": hackathon.format,
            "date": hackathon.date,
            "team_size": hackathon.team_size,
            "teams_registered": teams_count
        })

    return {
        "total_hackathons": total_hackathons,
        "total_users": total_users,
        "hackathons": hackathons_list
    }

#Предложить себя как тиммейта
@app.post("/users/me/teammate")
def create_teammate_profile(
        user_id: int = Query(...),
        db: Session = Depends(get_db)
):
    existing = db.query(TeammateRequest).filter(
        TeammateRequest.user_id == user_id,
        TeammateRequest.is_active == True
    ).first()

    if existing:
        existing.is_active = False
        db.commit()

    teammate_request = TeammateRequest(
        user_id=user_id,
        is_active=True
    )

    db.add(teammate_request)
    db.commit()
    db.refresh(teammate_request)

    return {
        "success": True,
        "message": "Ваш профиль добавлен в поиск тиммейтов",
        "id": teammate_request.id
    }

#Регистрация команды на хакатон
@app.post("/hackathons/{hackathon_id}/register-team")
def register_team_for_hackathon(
        hackathon_id: int,
        request: CreateTeamRequest,
        user_id: int = Query(...),
        db: Session = Depends(get_db)
):
    hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(404, "Хакатон не найден")

    if len(request.members) != 4:
        raise HTTPException(400, "Команда должна состоять из 4 участников")

    team_request = TeamRequest(
        hackathon_id=hackathon_id,
        team_name=request.team_name,
        description=request.description,
        created_by=user_id,
        is_active=True,
        in_dating=False
    )

    db.add(team_request)
    db.commit()
    db.refresh(team_request)

    for i, member in enumerate(request.members, 1):
        team_member = TeamMember(
            team_request_id=team_request.id,
            full_name=member.full_name,
            telegram_username=member.telegram_username,
            role=member.role,
            university=member.university,
            position=i
        )
        db.add(team_member)

    db.commit()

    return {
        "success": True,
        "message": "Команда успешно зарегистрирована на хакатон",
        "team_id": team_request.id
    }

#Регистрация команды в дейтинг
@app.post("/hackathons/{hackathon_id}/register-dating")
def register_team_for_dating(
        hackathon_id: int,
        request: CreateTeamRequest,
        user_id: int = Query(...),
        db: Session = Depends(get_db)
):
    hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(404, "Хакатон не найден")

    if len(request.members) != 4:
        raise HTTPException(400, "Команда должна состоять из 4 участников")

    team_request = TeamRequest(
        hackathon_id=hackathon_id,
        team_name=request.team_name,
        description=request.description,
        created_by=user_id,
        is_active=True,
        in_dating=True
    )

    db.add(team_request)
    db.commit()
    db.refresh(team_request)

    for i, member in enumerate(request.members, 1):
        team_member = TeamMember(
            team_request_id=team_request.id,
            full_name=member.full_name,
            telegram_username=member.telegram_username,
            role=member.role,
            university=member.university,
            position=i
        )
        db.add(team_member)

    db.commit()

    return {
        "success": True,
        "message": "Команда добавлена в дейтинг хакатона",
        "team_id": team_request.id
    }

# Получение списка команд для хакатона
@app.get("/hackathons/{hackathon_id}/teams-dating")
def get_dating_teams_for_hackathon(
        hackathon_id: int,
        db: Session = Depends(get_db)
):

    teams = db.query(TeamRequest).filter(
        TeamRequest.hackathon_id == hackathon_id,
        TeamRequest.is_active == True,
        TeamRequest.in_dating == True
    ).order_by(TeamRequest.created_at.desc()).limit(50).all()

    teams_list = []
    for team in teams:
        members = db.query(TeamMember).filter(
            TeamMember.team_request_id == team.id
        ).all()

        teams_list.append({
            "id": team.id,
            "team_name": team.team_name,
            "description": team.description,
            "team_photo_url": team.team_photo_url,
            "members": [
                {
                    "full_name": m.full_name,
                    "telegram_username": m.telegram_username,
                    "role": m.role,
                    "university": m.university
                }
                for m in members
            ],
            "created_by": team.created_by,
            "created_at": team.created_at.isoformat()
        })

    return {
        "success": True,
        "teams": teams_list,
        "total": len(teams_list)
    }

#Лайк или дизлайк команды
@app.post("/teams/{team_id}/action")
def like_dislike_team(
        team_id: int,
        request: LikeTeamRequest,
        user_id: int = Query(...),
        db: Session = Depends(get_db)
):
    team = db.query(TeamRequest).filter(TeamRequest.id == team_id).first()
    if not team:
        raise HTTPException(404, "Команда не найдена")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    if request.action == "like":
        team_creator = db.query(User).filter(User.id == team.created_by).first()

        notification_sent = False
        if team_creator and team_creator.telegram_id:
            try:
                from config import TELEGRAM_BOT_TOKEN
                import requests

                message = f"🎯 *Новый интерес к вашей команде!*\n\n"
                message += f"Пользователь *{user.name}* (@{user.telegram_username}) "
                message += f"заинтересовался вашей командой:\n"
                message += f"*'{team.team_name}'*\n\n"
                message += f"📨 *Свяжитесь с ним:* @{user.telegram_username}"

                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": team_creator.telegram_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }

                response = requests.post(url, json=payload, timeout=5)
                notification_sent = response.status_code == 200

            except Exception as e:
                print(f"❌ Ошибка отправки уведомления: {e}")
                notification_sent = False

        return {
            "success": True,
            "action": "like",
            "notification_sent": notification_sent
        }

    elif request.action == "dislike":
        return {
            "success": True,
            "action": "dislike"
        }
    else:
        raise HTTPException(400, "Неверное действие")


#лайк или дизлайк тиммейтов
@app.post("/teammates/{teammate_id}/action")
def like_dislike_teammate(
        teammate_id: int,
        request: TeammateLikeRequest,
        user_id: int = Query(...),
        db: Session = Depends(get_db)
):
    teammate_request = db.query(TeammateRequest).filter(
        TeammateRequest.id == teammate_id,
        TeammateRequest.is_active == True
    ).first()

    if not teammate_request:
        raise HTTPException(404, "Тиммейт не найден")

    liker = db.query(User).filter(User.id == user_id).first()
    if not liker:
        raise HTTPException(404, "Пользователь не найден")

    teammate_user = db.query(User).filter(User.id == teammate_request.user_id).first()
    if not teammate_user:
        raise HTTPException(404, "Пользователь тиммейта не найден")

    if request.action == "like":
        if teammate_user.telegram_id:
            try:
                from config import TELEGRAM_BOT_TOKEN
                import requests

                message = f"🎯 *Кто-то заинтересовался вами!*\n\n"
                message += f"Пользователь *{liker.name}* (@{liker.telegram_username}) "
                message += f"выразил интерес к вашему профилю тиммейта.\n\n"
                message += f"📨 *Свяжитесь с ним:* @{liker.telegram_username}"

                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": teammate_user.telegram_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }

                response = requests.post(url, json=payload, timeout=5)
                notification_sent = response.status_code == 200

            except Exception as e:
                print(f"❌ Ошибка отправки уведомления: {e}")
                notification_sent = False
        else:
            notification_sent = False

        return {
            "success": True,
            "action": "like",
            "notification_sent": notification_sent
        }

    elif request.action == "dislike":
        return {
            "success": True,
            "action": "dislike"
        }
    else:
        raise HTTPException(400, "Неверное действие")

# Получить последние 50 тиммейтов
@app.get("/teammates")
def get_all_teammates(
        db: Session = Depends(get_db)
):

    results = db.query(TeammateRequest, User).join(
        User, TeammateRequest.user_id == User.id
    ).filter(
        TeammateRequest.is_active == True
    ).order_by(TeammateRequest.created_at.desc()).limit(50).all()

    teammates_list = []
    for teammate_request, user in results:
        teammates_list.append({
            "id": teammate_request.id,
            "user_id": user.id,
            "name": user.name,
            "telegram_username": user.telegram_username,
            "photo_url": user.photo_url,
            "role": user.role,
            "level": user.level.value if user.level else None,
            "language": user.language.value if user.language else None,
            "city": user.city,
            "university": user.university,
            "about_text": user.about_text,
            "created_at": teammate_request.created_at.isoformat() if teammate_request.created_at else None
        })

    return {
        "success": True,
        "teammates": teammates_list,
        "total": len(teammates_list)
    }