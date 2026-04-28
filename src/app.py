import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())



from fastapi import FastAPI, HTTPException,Depends,BackgroundTasks
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore
from src.agent.graph.graph_loader import get_graph_with_tools
from src.schemas import chat,thread,messages
from src.agent.threads.thread import ThreadManagement
from langsmith import Client
from src.config.settings import settings
from src.service.chat_service import create_event_stream
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.agent.threads.thread import ThreadManagement
from src.agent.llms.groq import GroqLLM
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from src.custom_exception.exceptions import EntityAlreadyExistsError,EntityNotFoundError
from src.database.db import get_db_session
from psycopg_pool import AsyncConnectionPool
from langchain_huggingface import HuggingFaceEmbeddings
import logging
import os


# Create logs folder if it does not exist
os.makedirs("logs", exist_ok=True)

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),  # <-- LOG FILE
        logging.StreamHandler()               # <-- Also print to console
    ]
)

logger = logging.getLogger(__name__)

DB_URI = settings.DB_URI



# -----------------------------
# Lifespan with async context managers
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
     # ---- initialize LangSmith tracing ----
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "fastapi-genai-app"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY

    client = Client()
    print("LangSmith client initialized:", client)

    # --------------------------------------
    # A. Setup the Pool (Psycopg 3 Async)
    pool = AsyncConnectionPool(
        conninfo="postgresql://user:password@127.0.0.1:5444/vector_db",
        max_size=20,
        kwargs={"autocommit": True},
        open=False 
    )
    await pool.open()

    # B. Initialize Saver & Store
    checkpointer = AsyncPostgresSaver(pool)
    
    # Industrial Best Practice: Use the pool we just opened
    store = AsyncPostgresStore(
        pool,
        index={
            "dims": 768,
            "embed": HuggingFaceEmbeddings(model_name = "sentence-transformers/all-mpnet-base-v2"),
            "fields": ["content"]
        }
    )

    # C. Verification (Important!)
    await checkpointer.setup()
    await store.setup()
    
    builder = get_graph_with_tools()
    graph = builder.compile(checkpointer=checkpointer, store=store)
    thread_manager = ThreadManagement()
    extractor_llm = GroqLLM(
        model=settings.MODEL_NAME,
        api_key=settings.GROQ_API_KEY
        )
    llm = extractor_llm.get_llm()
    
        

    # D. Attach to App State
    app.state.pool = pool
    app.state.store = store
    app.state.checkpointer = checkpointer
    app.state.graph = graph
    app.state.thread_manager = thread_manager
    app.state.llm = llm


    yield # API is running

    # E. Cleanup
    await pool.close()


# -----------------------------
# Initialize FastAPI
# -----------------------------
app = FastAPI(title="LangGraph Workflow API", lifespan=lifespan)

@app.exception_handler(EntityAlreadyExistsError)
async def already_exists_handler(request: Request, exc: EntityAlreadyExistsError):
    return JSONResponse(
        status_code=409, 
        content={"error": "ALREADY_EXISTS", "detail": exc.message}
    )

@app.exception_handler(EntityNotFoundError)
async def not_found_handler(request: Request, exc: EntityNotFoundError):
    return JSONResponse(
        status_code=404, 
        content={"error": "NOT_FOUND", "detail": exc.message}
    )


# -----------------------------
# Chat endpoint
# -----------------------------
@app.post("/chat")
async def chat_endpoint(req: chat.MessageRequest,background_tasks:BackgroundTasks,db:AsyncSession=Depends(get_db_session)):
    graph = app.state.graph
    store = app.state.store
    llm = app.state.llm
    if graph is None:
        raise HTTPException(status_code=500, detail="Graph not initialized")

    event_stream = create_event_stream(req,graph,store,background_tasks,db,llm)
    return StreamingResponse(event_stream, media_type="text/event-stream")


@app.get("/fetch_threads/{user_id}",response_model=List[thread.ThreadRead])
async def fetch_threads(user_id:str,db:AsyncSession=Depends(get_db_session)):
    threads = await app.state.thread_manager.get_threads(db,user_id)
    return threads or []


@app.get("/fetch_messages/{thread_id}",response_model=List[messages.MessageRead])
async def fetch_messages(thread_id:str,db:AsyncSession=Depends(get_db_session)):
    messages = await app.state.thread_manager.get_messages(db,thread_id=thread_id)
    if messages:
        return messages
    raise HTTPException(status_code=404,detail="No conversation exist for user")

