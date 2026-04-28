
# def normalize_chunk(chunk, buffer_state):
#     """
#     Normalize chunk.
#     buffer_state: { "last": "previous_token_string" }
#     """
#     chunk_type = getattr(chunk, "type", None)
#     if not chunk_type:
#         return None

#     #chunk_type = chunk_type.lower()
#     content = getattr(chunk, "content", "") or ""

#     # Skip AI intermediate tool-call JSON
#     additional = getattr(chunk, "additional_kwargs", {}) or {}
#     if chunk_type == "ai" and (
#         additional.get("tool_calls") or getattr(chunk, "tool_calls", None)
#     ):
#         return None

#     # Skip empty AI chunks
#     if chunk_type == "ai" and not content.strip():
#         return None

#     # ---- FIX SPACING: only compare with last piece, not whole buffer ----
#     if chunk_type in ["AIMessageChunk", "ai"] and isinstance(content, str):
#         last = buffer_state.get("last", "")

#         piece = content.strip()

#         # Add missing space if needed
#         if last and not last.endswith(" ") and piece and not piece.startswith(" "):
#             piece = " " + piece

#         # Update only last chunk
#         buffer_state["last"] = piece
#         content = piece

#     # Build normalized dict
#     if chunk_type == "tool":
#             return {
#             "type": "tool",
#             "name": getattr(chunk, "name", None),
#             "content": content
#         }

#     if chunk_type in ["AIMessageChunk", "ai"]:
#             return {
#             "type": "ai",
#             "content": content
#         }

#     return None
def normalize_chunk(chunk, buffer_state):
    """
    Normalizes streamed chunks and fixes spacing issues.
    buffer_state = {"last": ""}
    """
    chunk_type = getattr(chunk, "type", None)
    if not chunk_type:
        return None

    content = getattr(chunk, "content", "") or ""

    # Skip tool-call metadata chunks
    additional = getattr(chunk, "additional_kwargs", {}) or {}
    if chunk_type == "ai" and (
        additional.get("tool_calls") or getattr(chunk, "tool_calls", None)
    ):
        return None

    # Skip empty chunks
    if chunk_type == "ai" and not content.strip():
        return None

    # ----------- FIX SPACING WITHOUT STRIPPING WRONG SPACES -----------
    if chunk_type in ["AIMessageChunk", "ai"] and isinstance(content, str):
        last = buffer_state.get("last", "")

        piece = content  # DO NOT STRIP

        # Case 1: If merging two word chunks like "Large" + "Language"
        if last and not last.endswith(" ") and piece and not piece.startswith((" ", ".", ",", "!", "?", ":", ";", "'")):
            piece = " " + piece

        # Case 2: If merging punctuation (e.g., "." + "Next")
        if last.endswith(("(", "[", "{", "/", "-", '“', '"', "'")):
            # No space needed
            pass

        # Update last piece
        buffer_state["last"] = last + piece
        content = piece

    # ------------------- Build normalized dict -------------------
    if chunk_type == "tool":
        return {
            "type": "tool",
            "name": getattr(chunk, "name", None),
            "content": content
        }

    if chunk_type in ["AIMessageChunk", "ai"]:
        return {
            "type": "ai",
            "content": content
        }

    return None

