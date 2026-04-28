from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession
from src.config.settings import settings


URL = settings.ASYNC_DB_URI
print("URL :" ,URL)

engine = create_async_engine(URL)

SessionLocal = async_sessionmaker(bind=engine,class_=AsyncSession,expire_on_commit=False)


async def get_db_session():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

