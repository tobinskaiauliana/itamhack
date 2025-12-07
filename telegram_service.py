import asyncio
from typing import Optional
from database import SessionLocal
from models import User
from config import TELEGRAM_BOT_TOKEN

class TelegramNotificationService:

    @staticmethod
    async def send_notification(telegram_id: int, message: str) -> bool:

        try:
            from telegram.ext import Application
            app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

            await app.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="Markdown"
            )
            print(f"✅ Уведомление отправлено пользователю {telegram_id}")
            return True

        except Exception as e:
            print(f"❌ Ошибка отправки уведомления пользователю {telegram_id}: {e}")
            return False

    @staticmethod
    async def send_invitation_notification(
            inviter_telegram_id: int,
            invitee_telegram_id: int,
            inviter_name: str,
            inviter_username: Optional[str],
            custom_message: Optional[str] = None
    ) -> bool:

        try:
            db = SessionLocal()
            invitee = db.query(User).filter(User.telegram_id == invitee_telegram_id).first()
            db.close()

            if not invitee:
                print(f"❌ Пользователь с telegram_id {invitee_telegram_id} не найден в базе")
                return False

            inviter_mention = f"@{inviter_username}" if inviter_username else inviter_name

            if custom_message:
                message = f"👋 *Приглашение в команду!*\n\n"
                message += f"*{inviter_name}* приглашает вас в свою команду.\n\n"
                message += f"*Сообщение:* {custom_message}\n\n"
                message += f"📨 *Контакты:* {inviter_mention}"
            else:
                message = f"👋 *Приглашение в команду!*\n\n"
                message += f"*{inviter_name}* приглашает вас в свою команду.\n\n"
                message += f"📨 *Свяжитесь с ним:* {inviter_mention}"

            return await TelegramNotificationService.send_notification(invitee_telegram_id, message)

        except Exception as e:
            print(f"❌ Ошибка отправки приглашения: {e}")
            return False

    @staticmethod
    async def send_team_interest_notification(
            team_creator_telegram_id: int,
            liker_user_id: int,
            team_name: str,
            liker_name: str,
            liker_username: Optional[str]
    ) -> bool:
        try:
            liker_mention = f"@{liker_username}" if liker_username else liker_name

            message = f"🎯 *Новый интерес к вашей команде!*\n\n"
            message += f"Пользователь *{liker_name}* заинтересовался вступлением в вашу команду:\n"
            message += f"*'{team_name}'*\n\n"
            message += f"📨 *Свяжитесь с ним:* {liker_mention}"

            return await TelegramNotificationService.send_notification(team_creator_telegram_id, message)

        except Exception as e:
            print(f"❌ Ошибка отправки уведомления о интересе: {e}")
            return False