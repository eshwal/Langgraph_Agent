from pydantic import BaseModel,ConfigDict
from datetime import datetime


class MessageBase(BaseModel):
    role: str
    content: str
    

class MessageCreate(MessageBase):
    thread_id: str

class MessageRead(MessageBase):
    message_id: int
    timestamp: datetime
    model_config=ConfigDict(from_attributes=True)


    
    