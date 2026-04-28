import datetime
import uuid
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs,DeclarativeBase):
    pass

class Thread(Base):
    __tablename__ = "conversation_threads"
    
    # Using a single UUID as PK is standard for GenAI threads
    thread_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True) # Who owns this thread
    title: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(),onupdate=func.now())

    # Relationship to get all messages in this thread
    messages: Mapped[list["Message"]] = relationship(back_populates="thread", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "conversation_messages"
    
    message_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("conversation_threads.thread_id"), index=True)
    
    role: Mapped[str] = mapped_column(String, index=True) # 'system', 'user', 'assistant'
    content: Mapped[str] = mapped_column(Text) # Use Text for long AI responses
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    thread: Mapped["Thread"] = relationship(back_populates="messages")