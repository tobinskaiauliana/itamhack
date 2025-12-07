import uvicorn
from app import app
import bot
import threading
import asyncio
import time

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


async def run_bot_async():
    from bot import main as bot_main
    await bot_main()


def run_bot():

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        loop.run_until_complete(run_bot_async())
    except KeyboardInterrupt:
        print("🤖 Бот остановлен")
    finally:
        loop.close()

if __name__ == "__main__":
    print("🚀 Запуск ITAM Hackathon Platform...")
    print("🌐 API сервер: http://0.0.0.0:8000")
    print("🤖 Telegram бот: запускается...")

    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    time.sleep(3)

    run_bot()