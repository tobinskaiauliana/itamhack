import uvicorn
from app import app
import bot
import threading

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)

def run_bot():
    bot.main()

if __name__ == "__main__":
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    run_bot()