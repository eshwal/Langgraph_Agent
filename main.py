# run_app.py
import asyncio
import selectors
from uvicorn import Config, Server
from src.app import app  # your FastAPI + LangGraph app

# Force selector event loop (psycopg compatible)
loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
asyncio.set_event_loop(loop)

config = Config(app=app, host="127.0.0.1", port=8000, workers=1, loop="asyncio")
server = Server(config)

loop.run_until_complete(server.serve())
