import uvicorn
from app import app
import bot
import threading
import asyncio

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def run_bot():
    bot.main()


if __name__ == "__main__":
    print("🚀 Запуск ITAM Hackathon Platform...")
    print("🌐 API сервер: http://0.0.0.0:8000")
    print("🤖 Telegram бот: запускается...")

    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    run_bot()