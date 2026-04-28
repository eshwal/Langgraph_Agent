import requests
import json

FASTAPI_URL = "http://localhost:8000"

def stream_chat(user_id: str, thread_id: str,user_input:str):
    url = f"{FASTAPI_URL}/chat"
    payload = {
        "user_input": user_input,
        "user_id": user_id,
        "thread_id": thread_id
    }
    print(payload)
    with requests.post(url, json=payload, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                yield data

def get_threads(user_id: str):
    url = f"{FASTAPI_URL}/fetch_threads/{user_id}"
    if requests.get(url):
        return requests.get(url).json()
    else:
        return []

def get_messages(user_id: str,thread_id:str):
    url = f"{FASTAPI_URL}/fetch_messages/{thread_id}"
    response = requests.get(url)
    if response:
        return response.json()
    else:
        return []
