import streamlit as st
from langchain_core.messages import AIMessage,ToolMessage
import uuid
from api_sync import get_messages,get_threads,stream_chat
# Example user (replace with login/session logic if needed)
CURRENT_USER_ID = 1

# 🔹 Utility Functions
def get_thread_id():
    """Generate a unique thread ID."""
    return str(uuid.uuid4())

def reset_chat():
    """Reset the chat for a new thread."""
    new_thread = get_thread_id()
    st.session_state['current_thread'] = new_thread
    st.session_state['threads_data'][new_thread] = []

# 🔹 Session State Initialization
if 'current_user_id' not in st.session_state:
    st.session_state['current_user_id'] = CURRENT_USER_ID

if 'existing_threads' not in st.session_state:
    st.session_state['existing_threads'] = get_threads(CURRENT_USER_ID)

if 'all_threads' not in st.session_state:
    st.session_state['all_threads'] = list(st.session_state['existing_threads'])

if 'threads_data' not in st.session_state:
    st.session_state['threads_data'] = {}

if 'current_thread' not in st.session_state:
    new_thread = get_thread_id()
    st.session_state['current_thread'] = new_thread
    st.session_state['threads_data'][new_thread] = []

# 🔹 Sidebar UI
def render_sidebar():
    st.sidebar.title("💬 My Chatbot")
    if st.sidebar.button("➕ New Chat"):
        reset_chat()

    st.sidebar.header("🗂 My Conversations")
    for thread in st.session_state['all_threads']:
        thread_id = thread["thread_id"]
        thread_title = thread.get("title", thread_id)

        if st.sidebar.button(thread_title, key=f"btn_{thread_id}"):
            st.session_state['current_thread'] = thread_id

            # Load from DB if needed
            if thread in st.session_state['existing_threads'] and thread_id not in st.session_state['threads_data']:
                thread_messages = get_messages(st.session_state['current_user_id'], thread_id)
                st.session_state['threads_data'][thread_id] = thread_messages

render_sidebar()

# 🔹 Main Chat Area
st.title("🤖 Ask Your Queries Here")
thread_id = st.session_state['current_thread']
message_history = st.session_state['threads_data'].get(thread_id, [])

# Display message history
for msg in message_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 🔹 User Input Box
user_input = st.chat_input("Type your message here...", key="chat_input")

if user_input:
    # Append user message immediately
    user_msg = {"role": "user", "content": user_input}
    st.session_state['threads_data'][thread_id].append(user_msg)

    # Add or update thread title immediately
    existing_thread_ids = [t["thread_id"] for t in st.session_state['all_threads']]
    if thread_id not in existing_thread_ids:
        st.session_state['all_threads'].insert(0, {'thread_id': thread_id, 'title': user_input[:20]})
    else:
        for t in st.session_state['all_threads']:
            if t["thread_id"] == thread_id and not t.get("title"):
                t["title"] = user_input[:20]

    with st.chat_message("user"):
        st.write(user_input)

    
    with st.chat_message("assistant"):
        # 1. RESERVE SLOTS: This prevents jumping.
        # Text placeholder is first, so it will ALWAYS be at the top.
        text_placeholder = st.empty() 
        status_placeholder = st.empty()
        
        full_response = ""
        tool_outputs = []

        # 2. DEFINE THE FILTERED GENERATOR
        def filtered_stream():
            import re
            for chunk in stream_chat(str(st.session_state['current_user_id']), thread_id, user_input):
                
                # --- HANDLE TOOLS (XML & JSON Filtering) ---
                if chunk.get("type") == "tool":
                    tool_outputs.append(chunk)
                    continue
                
                # --- HANDLE AI TEXT ---
                if chunk.get("type") == "ai":
                    content = chunk.get("content", "")
                    
                    # STOPS THE XML LEAK: Remove <web_search>...</web_search> and the tags
                    clean_content = re.sub(r'<.*?>', '', content)
                    # Also strip out raw JSON if it's still leaking
                    if clean_content.strip().startswith('{') and clean_content.strip().endswith('}'):
                        continue

                    if clean_content:
                        yield clean_content

        # 3. EXECUTE STREAM: This restores auto-scroll
        with text_placeholder:
            ai_message = st.write_stream(filtered_stream())

        # 4. RENDER TOOLS: These will now appear BELOW the text because 
        # the status_placeholder was defined after text_placeholder.
        if tool_outputs:
            with status_placeholder:
                for tool in tool_outputs:
                    with st.status(f"🔧 Used {tool.get('name', 'Search')}", expanded=False):
                        st.write(tool.get("content"))
   
    # with st.chat_message("assistant"):
    #     # Stream chunks
    #     status_holder = {"box": None}

    #     def ai_only_stream():
    #         for chunk in stream_chat(
    #         str(st.session_state['current_user_id']),
    #         thread_id,
    #         user_input,
    #     ):
    #             # Lazily create & update the SAME status container when any tool runs
    #             if chunk.get("type")=="tool":
    #                 tool_name = chunk.get("name", "tool")
    #                 if status_holder["box"] is None:
    #                     status_holder["box"] = st.status(
    #                         f"🔧 Using `{tool_name}` …", expanded=True
    #                     )
                    
    #                 else:
    #                     status_holder["box"].update(
    #                         label=f"🔧 Using `{tool_name}` …",
    #                         state="running",
    #                         expanded=True,
    #                     )
             
    #                 with status_holder["box"]:
    #                     st.markdown(f"**Tool output:**\n\n{chunk.get("content")}")
    #                 yield ""

    #             # Stream ONLY assistant tokens
    #             elif chunk.get("type")=="ai":
    #                 if chunk.get("content","").strip():
    #                     yield chunk.get("content")

    #     ai_message = st.write_stream(ai_only_stream())
        
    #      # Finalize only if a tool was actually used
    #     if status_holder["box"] is not None:
    #         status_holder["box"].update(
    #             label="✅ Tool finished", state="complete", expanded=False
    #         )

    # ✅ Store only final AI message after streaming
    if ai_message.strip():
        st.session_state['threads_data'][thread_id].append({"role": "ai", "content": ai_message})
