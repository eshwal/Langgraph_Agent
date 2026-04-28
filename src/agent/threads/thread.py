from sqlalchemy.ext.asyncio import AsyncSession
from src.models.conversation import Thread,Message
from src.schemas import messages,thread
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.custom_exception.exceptions import EntityNotFoundError


class ThreadManagement:
    """ Manage user threads and user chat message"""
    async def save_message(self, db: AsyncSession, thread_id: str, role: str, content: str):
        # 1. Validate using Schema (Good practice!)
        msg_data = messages.MessageCreate(
            role=role, 
            content=content, 
            thread_id=thread_id
        )
        # 2. Convert to Model for saving
        new_message = Message(**msg_data.model_dump())
        db.add(new_message)
        
        try:
            # flush allows us to check for FK constraints without committing the whole transaction
            await db.flush()
            #await db.refresh(new_message)
            return new_message
        except IntegrityError:
            # If thread_id doesn't exist in the Thread table
            raise EntityNotFoundError("Thread", thread_id)

    
    async def save_thread(self, db: AsyncSession, thread_id: str, user_id: str, title: str):
        # Check if thread already exists
        existing_thread = await db.get(Thread, thread_id)
        if existing_thread:
            return existing_thread

        thread_data = thread.ThreadCreate(
            user_id=user_id,
            title=title,
            thread_id=thread_id
        )
        new_thread = Thread(**thread_data.model_dump())
        db.add(new_thread)    
        
        try:
            await db.flush()
            #await db.refresh(new_thread)
            return new_thread
        except IntegrityError:
            # In case of a race condition where it was created between 'get' and 'add'
            await db.rollback()
            return await db.get(Thread, thread_id)

    

    async def get_messages(
        self,
        db: AsyncSession, 
        thread_id: str
    ):
        thread_obj = await db.get(Thread, thread_id)
        if not thread_obj:
            raise EntityNotFoundError("Thread", thread_id)
    
        stmt = select(Message).where(Message.thread_id==thread_id).order_by(Message.timestamp.asc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_threads(
        self,
        db: AsyncSession, 
        user_id :str
    ):
    
        stmt = select(Thread).where(Thread.user_id==user_id).order_by(Thread.updated_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_formatted_history(self, db: AsyncSession, thread_id: str):
        messages = await self.get_messages(db, thread_id)
        if not messages:
            # Optionally check if thread exists to raise EntityNotFoundError
            thread_obj = await db.get(Thread, thread_id)
            if not thread_obj:
                raise EntityNotFoundError("Thread", thread_id)
        
        return [{"role": m.role, "content": m.content} for m in messages]
                



