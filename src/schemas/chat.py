from pydantic import BaseModel
#-----------------------------
# Request body model
# -----------------------------
class MessageRequest(BaseModel):
    user_id: str
    thread_id: str
    user_input: str
