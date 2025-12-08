import uvicorn
from app import app
import threading
import subprocess
import sys
import time


def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def run_bot():
    """Запуск бота в отдельном процессе"""
    print("🤖 Запуск Telegram бота...")
    subprocess.run([sys.executable, "-m", "bot"])


if __name__ == "__main__":
    print("🚀 Запуск ITAM Hackathon Platform...")
    print("🌐 API сервер: http://0.0.0.0:8000")

    # Запускаем API в отдельном потоке
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    time.sleep(3)

    # Запускаем бота в основном потоке
    run_bot()