from langchain.messages import HumanMessage
from src.helpers.chunk_normalizer import normalize_chunk
import json
from fastapi import BackgroundTasks
from src.background.long_term_mem import store_long_term_pref
from sqlalchemy.ext.asyncio import AsyncSession

def create_event_stream(req,graph,store,background_tasks:BackgroundTasks,db:AsyncSession,llm):

    config = {
        "configurable": {
            "thread_id": req.thread_id,
            "user_id": req.user_id,
            "token_limit": 8000,
            "display_count": 4,
            "db": db
        }
    }
    

    # Stream results from graph
    async def event_stream():
        buffer_state = {"last": ""}  # only store last emitted piece

        async for chunk, metadata in graph.astream(
            {"messages": [HumanMessage(content=req.user_input)]}, 
            config, 
            stream_mode="messages"
            ):

            # Identify which node is currently 'speaking'
            source_node = metadata.get("langgraph_node")

            # ✅ ONLY allow these nodes to reach the user
            # This keeps 'summarize', 'increment', and 'prepare_context' silent.
            # In your event_stream logic
            if source_node in ["chat", "tools", "end_chat"]:
                # 1. Check if the chunk is an AI Message with tool_calls (The "Thinking" phase)
                # We want to SKIP sending tool_calls as 'ai' content to avoid raw JSON in UI
                if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    # Optionally send a 'status' type so the UI knows a tool is STARTING
                    tool_name = chunk.tool_calls[0]["name"]
                    yield json.dumps({"type": "status", "content": f"Calling {tool_name}..."}) + "\n"
                    continue 

                # 2. Check if the chunk is a ToolMessage (The "Result" phase)
                if source_node == "tools":
                    # Ensure your normalize_chunk identifies this as type="tool"
                    data = normalize_chunk(chunk, buffer_state) 
                    if data:
                        yield json.dumps(data) + "\n"
                    continue

                # 3. Regular AI text content
                data = normalize_chunk(chunk, buffer_state)
                if data and data.get("type") == "ai":
                    yield json.dumps(data) + "\n"



    #   # 2. 🔥 STREAM IS DONE - Fetch the ACTUAL full state from the checkpointer
        full_graph_state = await graph.aget_state(config)
        
        # full_graph_state.values contains your 'messages', 'counter', 'summary', etc.
        final_values = full_graph_state.values

        print("FINAL state keys:", final_values.keys())

        messages = final_values.get("messages", [])

        # Best Practice: Trigger every 6-10 human messages, 
        # or if specifically requested by a node.
        MESSAGE_THRESHOLD = 4
        human_msg_count = len([m for m in messages if isinstance(m, HumanMessage)])

        if human_msg_count > 0 and human_msg_count % MESSAGE_THRESHOLD == 0:
            background_tasks.add_task(
                store_long_term_pref,
                final_values, 
                store,
                llm,
                user_id = req.user_id
            )

    return event_stream()