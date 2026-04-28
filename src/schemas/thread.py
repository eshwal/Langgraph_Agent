from pydantic import BaseModel,ConfigDict
from datetime import datetime


class ThreadBase(BaseModel):
    title: str

class ThreadCreate(ThreadBase):
    thread_id: str
    user_id: str

class ThreadRead(ThreadBase):
    thread_id: str
    user_id: str
    created_at : datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)



