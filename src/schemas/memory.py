# from pydantic import BaseModel,Field
# from typing_extensions import Literal,List

# from enum import Enum
# from typing import List
# from pydantic import BaseModel, Field

# # 1. Use an actual Enum class (Groq prefers this for validation)
# class MemoryCategory(str, Enum):
#     user_profile = "user_profile"
#     user_preferences = "user_preferences"
#     project_context = "project_context"

# class Fact(BaseModel):
#     # Use the Enum here
#     topic: MemoryCategory = Field(
#         description="Must be 'user_profile', 'user_preferences', or 'project_context'."
#     )
#     content: str
#     is_update: bool

# class MemoryExtraction(BaseModel):
#     facts: List[Fact]

# from enum import Enum
# from typing import List
# from pydantic import BaseModel, Field

# class MemoryCategory(str, Enum):
#     user_profile = "user_profile"
#     user_preferences = "user_preferences"
#     project_context = "project_context"

# class Fact(BaseModel):
#     topic: MemoryCategory
#     content: str = Field(description="For user_profile, provide a full descriptive sentence. For others, keep it atomic sentences.")
#     is_update: bool = Field(description="True if the user is correcting or changing previous info.")
#     is_explicit: bool = Field(
#         description="True ONLY if the user explicitly stated this about themselves (e.g., 'I am', 'I like', 'My project is'). False if they just asked a question."
#     )

# class MemoryExtraction(BaseModel):
#     facts: List[Fact] = Field(default_factory=list)


# from enum import Enum
# from typing import List, Optional
# from pydantic import BaseModel, Field

# class MemoryCategory(str, Enum):
#     user_identity = "user_identity"
#     user_preferences = "user_preferences"
#     project_goal = "project_goal"

# class Fact(BaseModel):
#     """A single atomic fact about the user's identity or preferences."""
#     topic: str = Field(description="Must be exactly: 'user_identity', 'user_preferences', or 'project_goal'")
#     content: str = Field(description="The factual statement.")
#     is_update: bool = Field(description="True if this updates previous info.")
#     is_explicit: bool = Field(description="True if user explicitly stated this.")
#     significance: int = Field(description="1-5 rating of importance.")

# class MemoryExtraction(BaseModel):
#     facts: List[Fact] = Field(default_factory=list)



from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class MemoryCategory(str, Enum):
    user_identity = "user_identity"
    user_preferences = "user_preferences"
    project_goal = "project_goal"

class Fact(BaseModel):
    topic: str = Field(description="Exactly: 'user_identity', 'user_preferences', or 'project_goal'")
    content: str = Field(description="Atomic sentence for fact discovered.")
    is_update: bool = Field(description="True if this updates existing info.")
    is_explicit: bool = Field(description="True if the user stated this directly.")
    significance: int = Field(description="Importance 1-5.")

    @field_validator("significance")
    @classmethod
    def scale_significance(cls, v):
        # Failsafe: ensures Llama stays within 1-5 range
        return max(1, min(5, v))

class MemoryExtraction(BaseModel):
    facts: List[Fact] = Field(default_factory=list)