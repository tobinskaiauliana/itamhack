from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database import SessionLocal
from auth_service import AuthService

TELEGRAM_BOT_TOKEN = "8298815335:AAELJ2jZVSYcFTcxomwqZmuBhqd3_aw3IGU"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name or user.username}!\n\n"
        f"Используй команду /code чтобы получить код для входа на сайт."
    )

async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    db = SessionLocal()
    try:
        auth_code = AuthService.create_auth_code(
            db=db,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

        PUBLIC_URL = "https://cdcef7fd2f0454.lhr.life" #!!!!!!!!!не забыть поменять
        login_url = f"{PUBLIC_URL}/auth/telegram?code={auth_code.code}"

        keyboard = [
            [InlineKeyboardButton("🔐 Войти на сайт", url=login_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ *Код создан!*\n\n"
            f"🔐 Ваш код: `{auth_code.code}`\n"
            f"⏰ Действует 5 минут\n\n"
            f"Нажмите кнопку ниже для входа:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

        print(f"📱 Код {auth_code.code} создан для пользователя {user.id}")

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при создании кода.\n"
            "Попробуйте еще раз или обратитесь к администратору."
        )
    finally:
        db.close()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Доступные команды:*\n\n"
        "`/start` - Начать работу с ботом\n"
        "`/code` - Получить код для входа на сайт\n"
        "`/help` - Показать это сообщение\n\n"
        "После получения кода перейдите на сайт и введите его.",
        parse_mode="Markdown"
    )


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("code", code_command))
    application.add_handler(CommandHandler("help", help_command))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()