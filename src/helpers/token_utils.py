import tiktoken


def count_tokens(messages, model_name="gpt-4"):
    text = "\n".join(m.content for m in messages)
    try:
        enc = tiktoken.encoding_for_model(model_name)
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4