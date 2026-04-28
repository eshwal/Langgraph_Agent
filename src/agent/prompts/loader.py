from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from src.agent.prompts.SystemPrompt import prompt3


def load_prompt():
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=prompt3),
        MessagesPlaceholder(variable_name="messages")
        ])