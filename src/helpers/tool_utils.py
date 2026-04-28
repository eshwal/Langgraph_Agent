from langchain.messages import AIMessage


# def check_tool_calls(response):
#     tool_calls = getattr(response, 'tool_calls', None) or []
#     if not tool_calls:
#         if hasattr(response, 'additional_kwargs') and 'tool_calls' in response.additional_kwargs:
#             tool_calls = response.additional_kwargs.get('tool_calls', [])

#     # Fallback: parse content for function-like markers
#     if isinstance(response, AIMessage) and ("<" in response.content and "</function>" in response.content):
#         tool_calls = ["detected_in_content"]

#     return tool_calls

import re
from langchain.messages import AIMessage
import logging

logger = logging.getLogger(__name__)

# TOOL_CALL_PATTERN = re.compile(
#     r"<(\w+)>\s*({.*?})\s*</function>", 
#     re.DOTALL
# )

# def check_tool_calls(response):
#     # 1. Clean structured tool_calls first
#     tool_calls = getattr(response, "tool_calls", None) or []

#     # 2. Check additional_kwargs
#     if not tool_calls:
#         if hasattr(response, "additional_kwargs") and "tool_calls" in response.additional_kwargs:
#             tool_calls = response.additional_kwargs["tool_calls"] or []

#     # 3. Fallback: detect malformed tool call via regex
#     if isinstance(response, AIMessage):
#         content = (response.content or "").strip()
#         if TOOL_CALL_PATTERN.search(content):
#             tool_calls = ["detected_in_content"]

#     return tool_calls

# This matches <any_tag>{json}</any_tag> OR <any_tag>{json} (without closing tag)
TOOL_CALL_PATTERN = re.compile(
    r"<(?P<tag>\w+)>\s*(?P<json>\{.*?\})(?:\s*</\1>)?", 
    re.DOTALL
)

def check_tool_calls(response):
    # 1. Standard LangChain tool_calls
    tool_calls = getattr(response, "tool_calls", None) or []
    if tool_calls:
        return tool_calls

    # 2. Check additional_kwargs (some models hide them here)
    if hasattr(response, "additional_kwargs") and "tool_calls" in response.additional_kwargs:
        t_calls = response.additional_kwargs["tool_calls"]
        if t_calls: return t_calls

    # 3. Robust Regex Fallback
    if isinstance(response, AIMessage):
        content = (response.content or "").strip()
        # Updated Regex to be more forgiving
        if TOOL_CALL_PATTERN.search(content):
            logger.debug(f"Regex detected tool call in content: {content[:50]}...")
            return ["detected_in_content"]

    return []
