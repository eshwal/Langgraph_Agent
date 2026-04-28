from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_URI: str
    ASYNC_DB_URI:str
    GROQ_API_KEY: str
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_TRACING: bool = True
    MODEL_NAME:str = "llama-3.1-8b-instant"
    #MODEL_NAME:str = "llama-3.3-70b-versatile"


    class Config:
        env_file=".env"


settings = Settings()


