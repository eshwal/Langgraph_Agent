from src.agent.state.chatstate import ChatState
from src.agent.llms.groq import GroqLLM
from src.agent.threads.thread import ThreadManagement
from src.helpers.token_utils import count_tokens
from src.helpers.tool_utils import check_tool_calls
from langchain.messages import SystemMessage,AIMessage,HumanMessage
from langchain.messages import RemoveMessage,trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.config import get_store
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

class GraphNode:
    MAX_ITER = 2
    MODEL_MAX_TOKENS=8000
    SUMMARIZE_TOKENS = 400
    SUMMARIZE_TRIGGER_TOKENS = 4000
    CONTEXT_BUDGET = 2000
    SAFETY_MARGIN=1500
    HISTORY_BUDGET = 4000    # (TOTAL - SAFETY_MARGIN - CONTEXT)

    def __init__(self,llm,llm_with_tools):
        self.llm = llm
        self.llm_with_tools = llm_with_tools
        self.thread_manager = ThreadManagement()
    
    # -------------------------
    # Summarize Node
    # -------------------------
    async def summarize(self,state:ChatState):
        msg = state['messages']
        summary = state.get('summary','')
        to_summarize = msg[:-2]
    
        if summary !='':
            prompt= f'Summarize the current chat_history in {self.SUMMARIZE_TOKENS} so that a rolling summary can be created.\n Existing summary: {summary}.\n Chat_history: {to_summarize}'
        else:
            prompt = f'Summarize the current chat history in {self.SUMMARIZE_TOKENS} without missing out any important details. Chat_history : {to_summarize}'
    
        summary = await self.llm.ainvoke(prompt)

        messages = [RemoveMessage(id=m.id) for m in to_summarize]

        return {'messages':messages,'summary':summary.content}
    
    # -------------------------
    # Decide Node for Summarization
    # -------------------------
    async def should_summarize(self,state:ChatState):
        msg = state['messages']
        if count_tokens_approximately(msg) > self.SUMMARIZE_TRIGGER_TOKENS:
            return "summarize"
        else:
            return "chat"


    # -------------------------
    # Prepare context node
    # -------------------------
    async def prepare_context(self, state: ChatState, config):
        """Runs ONCE at the start of the graph."""
        logger.debug("INSIDE PREPARE CONTEXT NODE --------")
        cfg = config.get("configurable")
        user_id = cfg["user_id"]
        store = get_store()
        messages = state.get("messages", [])

        print(store)
        
        # We only care about the very last human message for searching memory
        last_human_msg = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        print(last_human_msg)
        context_blocks = []

        # 1. Add Summary
        if state.get("summary"):
            context_blocks.append(f"HISTORICAL CHAT SUMMARY (Internal Use Only - Do not repeat to user):\n{state['summary']}")

        # 2. Retrieve Memory
        if store and last_human_msg:
            namespace = ("memories", user_id)
            try:
                profile = await store.aget(namespace, "core_profile")
                print("PROFILE",profile)
                if profile:
                    context_blocks.append(f"USER PROFILE: {profile.value['content']}")

                relevant_facts = await store.asearch(namespace, query=last_human_msg, limit=2)
                facts = "\n".join(m.value["content"] for m in relevant_facts if m.key != "core_profile")
                if facts:
                    context_blocks.append(f"RELEVANT FACTS: {facts}")
            except Exception as e:
                logger.error(f"Memory retrieval failed: {e}")

        # 3. Combine into a single string
        dynamic_context_str =  "\n\n".join(context_blocks) if context_blocks else ""

        # if dynamic_context_str:
        #     dynamic_context_str = "Use the USER PROFILE to address the user naturally and stay in character." \
        # "Use the HISTORICAL CHAT SUMMARY only for context; never repeat it back to the user." \
        # "Use Relevant context to personalize answer according to each user." \
        # "If you know the user's name from the profile, use it (e.g., 'Sure, [Name]').\n\n"+dynamic_context_str
            
        if dynamic_context_str:
                dynamic_context_str = (
            "### CURRENT USER CONTEXT (PRIORITY).Use the HISTORICAL CHAT SUMMARY only for context; never repeat it back to the user.\n"
            f"{dynamic_context_str}\n\n"
            "### PERSONALIZATION TASK:\n"
            "1. Address the user by name.\n"
            "2. Incorporate RELEVANT FACTS or PREFERENCES from above into your explanation.\n"
            "3. Adjust your technical depth based on the USER PROFILE."
    )

        # 4.Hard character cap to ensure it stays within 2500 tokens
        char_cap = self.CONTEXT_BUDGET * 4
        if len(dynamic_context_str) > char_cap:
            dynamic_context_str = dynamic_context_str[:char_cap] + "...[Truncated]"
        
        # We pass this string forward in llm_input
        return {"llm_input": dynamic_context_str, "counter": 0}
    

    # async def prepare_context(self,state:ChatState,config):
    #     cfg = config.get("configurable")
    #     user_id = cfg["user_id"]
    #     token_limit = self.MODEL_MAX_TOKENS - self.SAFETY_MARGIN
    #     store = cfg.get("store")
    #     messages = state.get("messages",[])
    #     last_msg = messages[-1] if messages else None

    #     # Trim messages first to fit token limit
    #     messages=trim_messages(messages, 
    #                   max_tokens=token_limit, 
    #                   strategy="last", 
    #                   token_counter=count_tokens_approximately, 
    #                   include_system=True)

    #     # Prepare context: summary + memory
    #     context_blocks = []

    #     if state.get("summary"):
    #         context_blocks.append("HISTORICAL CHAT SUMMARY (Internal Use Only - Do not repeat to user):\n"f"{state['summary']}")

    #     if store and isinstance(last_msg, HumanMessage):
    #         namespace = ("memories", user_id)
    #         try:
    #             # Retrieve user profile
    #             profile = await store.aget(namespace, "core_profile")
    #             if profile:
    #                 profile_content = profile.value["content"]
    #                 context_blocks.append(f"USER PROFILE/IDENTITY:\n{profile_content}")

    #             # Retrieve relevant past facts
    #             relevant_facts = await store.asearch(namespace, query=last_msg.content, limit=2)
    #             facts_content = "\n".join(m.value["content"] for m in relevant_facts if m.key != "core_profile")
    #             if facts_content:
    #                 context_blocks.append(f"Relevant context:\n{facts_content}")

    #         except Exception as e:
    #             logger.error(f"Memory retrieval failed: {e}", exc_info=True)

    #     # Build context system message
    #     if context_blocks:
    #         context_message = SystemMessage(
    #             content=(
    #             "Use the USER PROFILE to address the user naturally and stay in character. "
    #             "Use the HISTORICAL CHAT SUMMARY only for context; never repeat it back to the user. "
    #             "Use Relevant context to personalize answer according to each user"
    #             "If you know the user's name from the profile, use it (e.g., 'Sure, [Name]').\n\n"
    #             "<CONTEXT>\n" + 
    #                 "\n\n".join(context_blocks) +
    #                 "\n</CONTEXT>"
    #             )
    #         )
    #         # Prepend context message to state messages
    #         messages = [context_message] + messages

    #     # Trim again to ensure total tokens under limit
    #     messages = trim_messages(messages, max_tokens=token_limit, strategy="last", token_counter=count_tokens_approximately, include_system=True)

    #     return {"llm_input":messages,"counter":0}

    # -------------------------
    # Chat LLM Node
    # -------------------------
    async def chat_llm(self, state: ChatState, *, config):
        logger.debug("Entering chat node")
        
        # 1. Get the dynamic context string from prepare_context
        dynamic_context = state.get("llm_input", "")
        
        # 2. Get the actual conversation history from state
        # Filter out SystemMessages to prevent them from "stacking up" in loops
        clean_history = [m for m in state.get("messages", []) if not isinstance(m, SystemMessage)]

        
        # 3. Trim History to 4,000 tokens
        # Strategy 'last' ensures the most recent Tool results and Human questions stay.
        trimmed_history = trim_messages(
            clean_history,
            max_tokens=self.HISTORY_BUDGET,
            strategy="last",
            token_counter=count_tokens_approximately
        )
        
        
        # 4. Construct the Final Payload
        # We 'sandwich' the static context as a SystemMessage at the top.
        final_payload = []
        if dynamic_context:
            final_payload.append(SystemMessage(content=f"INSTRUCTIONS/CONTEXT:\n{dynamic_context}"))
        
        final_payload.extend(trimmed_history)

       

        try:
            # IMPORTANT: Because your prompt has MessagesPlaceholder(variable_name="messages"),
            # you MUST pass a dictionary with that key.
            input_dict = {"messages": final_payload}
            
            response = await self.llm_with_tools.ainvoke(input_dict)
            return {"messages": [response]}
            
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}", exc_info=True)
            return {"messages": [AIMessage(content="⚠️ I'm sorry, I'm having trouble connecting right now.")]}
        

    # async def chat_llm(self, state: ChatState,*,config):
    #     logger.debug("Entering chat node")
    #     # count = state.get("counter",0)
    #     # if count >= self.MAX_ITER:
    #     #     return
    #     prompt = state.get("llm_input", state["messages"])
    #     try:
    #         response = await self.llm_with_tools.ainvoke(prompt)
    #     except Exception as e:
    #         logger.error(f"LLM invocation failed: {e}", exc_info=True)
    #         response = AIMessage(content="⚠️ Sorry, something went wrong.")

    #     logger.debug("Exiting chat node")
    #     return {"messages": [response]}

    # ---------------------------
    # Increment Node
    # ---------------------------
    def increment_counter(self,state: ChatState):
        logger.debug("Entering increment_counter node")
        state["counter"] = state.get("counter", 0) + 1
        logger.debug("Exiting increment_counter node")
        return state

   
    # async def check_tool_end(self, state: ChatState,*,config):
    #     logger.debug("Entering check_tool_end node")
    #     count = state.get("counter", 0)
    #     last_message = state["messages"][-1]

    #     # 1. If final answer (no tool call + has content) → END
    #     if isinstance(last_message, AIMessage):
    #         tool_calls = check_tool_calls(last_message)
    #         content = (last_message.content or "").strip()
    #         if not tool_calls and content:
    #             logger.debug("Received Final Answer with no more tool calls.") 
    #             logger.debug("Ending Graph Invocation...")   
    #             return "persist"

    #     # 2. If tool call requested:
    #     tool_calls = check_tool_calls(last_message)
    #     if isinstance(last_message, AIMessage) and tool_calls:
    #         # Allow tool call only if under MAX_ITER
    #         if count < GraphNode.MAX_ITER:
    #             logger.debug("Count less than MAX_ITER and Tool calls present")
    #             logger.debug("Calling Tool...")                 
    #             return "increment"
    #         else:
    #             logger.debug("MAX_ITER crossed")
    #             logger.debug("Calling End Chat...")
    #             return "end_chat"   # fallback summarizer

    #     # 3. If max_iter reached but last message is empty/invalid → fallback
    #     if count >= GraphNode.MAX_ITER:
    #         logger.debug("MAX_ITER crossed")
    #         logger.debug("Calling End Chat...")
    #         return "end_chat"

    #     # 4. Default safe exit
    #     return "persist"
    
    

    async def check_tool_end(self, state: ChatState, *, config):
        last_message = state["messages"][-1]
        count = state.get("counter", 0)
        
        # Priority 1: If there's a tool call, we MUST process it (if counter allows)
        tool_calls = check_tool_calls(last_message)
        
        if tool_calls:
            if count < GraphNode.MAX_ITER:
                logger.debug(f"Tool call detected (Iter: {count}). Routing to 'increment'.")
                return "increment"
            else:
                logger.debug("MAX_ITER reached with pending tool calls. Routing to 'end_chat'.")
                return "end_chat"

        # Priority 2: No tool calls found. Is there a final answer?
        content = (getattr(last_message, "content", "") or "").strip()
        if content:
            logger.debug("No tool calls found. Content present. Routing to 'persist'.")
            return "persist"

        # Priority 3: Safety Fallback (Empty message or confusing state)
        return "persist"


#     async def end_chat(self, state: ChatState, *, config=None):
#        
        
#         

#         prompt = [SystemMessage(content="Summarize the final results for the user.")] + trimmed_all
#         response = await self.llm.ainvoke(prompt)
#         return {"messages": [response]}


    #######################
    # End Chat node
    #######################
    async def end_chat(self, state: ChatState, *, config=None):
        logger.debug("Entering End Chat State - Final Synthesis")
        
        # 2. Trim messages to fit context
        safe_limit = self.MODEL_MAX_TOKENS - 1000
        trimmed_all = trim_messages(
            state["messages"],
            max_tokens=safe_limit,
            strategy="last",
            token_counter=count_tokens_approximately
        )

        # 3. Use a "Commander" Prompt to force an answer
        # We explicitly tell it to ignore the pending search.
        instruction = (
            "The search window is now CLOSED. You must provide a final, direct answer to the user now. "
            "Do not ask for more tools. Do not output XML. Use your internal knowledge and the "
            "information already gathered in the thread to explain the topic (e.g., Artificial Intelligence) clearly."
        )
        
        # We append a specific "Final Answer Request" message to the very end
        # to break the model's 'waiting' loop.
        final_msgs = [SystemMessage(content=instruction)] + trimmed_all
        final_msgs.append(HumanMessage(content="Please give me your best final answer based on what we have so far."))

        # 4. Invoke the model WITHOUT tool binding
        # Use self.llm (the raw model), NOT self.llm_with_tools.
        response = await self.llm.ainvoke(final_msgs)
        
        # 5. The "Safety Catch"
        # If it still gives an empty string, we provide a basic fallback.
        if not response.content or len(response.content.strip()) < 5:
            response.content = "I've reached my search limit for this session, but based on what we've discussed so far..."
        logger.debug("Exiting End Chat Node with final content.")
        return {"messages": [response]}


    # async def end_chat(self,state: ChatState, *, config=None):
    #     logger.debug("Entering End Chat State")

    #      # Reserve 1000 tokens for the final summary output
    #     safe_limit = self.MODEL_MAX_TOKENS - 1000

    #     #We trim EVERYTHING (including context) to fit the final summary call
    #     trimmed_all = trim_messages(
    #         state["messages"],
    #         max_tokens=safe_limit,
    #         strategy="last",
    #         token_counter=count_tokens_approximately
    #     )

    #     system_prompt = SystemMessage(content=(
    #     "Summarize the entire conversation and produce a clear, natural final answer. "
    #     "You may use relevant details from all messages (human, AI, and tools), "
    #     "but do not explicitly label them or repeat their structure."
    #     ))
    #     prev_msgs = [system_prompt] + trimmed_all
    #     response = await self.llm.ainvoke(prev_msgs)
    #     logger.debug("Exiting End Chat Node")
    #     logger.debug("Ending Graph Invocation")
    #     return {"messages": [response]}
    
    # -------------------------
    # Finalize Node (store in DB / long term memory)
    # -------------------------
    async def persist_chat(self, state: ChatState, config):
        # 1. Retrieve the DB session passed via config
        db: AsyncSession = config.get("configurable", {}).get("db")
        if not db:
            raise RuntimeError("DB session not found in config. Ensure you pass it in ainvoke.")

        cfg = config["configurable"]
        user_id = cfg.get("user_id")
        thread_id = cfg.get("thread_id")

        messages = state.get("messages", [])
        last_user = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
        
        print("LAST USER",last_user,"LAST AI",last_ai)
        # 2. Persist - Save Thread first (Foreign Key Requirement)
        if last_user:
            # Title is first 20 chars of user input
            await self.thread_manager.save_thread(
                db, 
                thread_id=thread_id, 
                user_id=user_id, 
                title=last_user.content[:20]
            )
            
            await self.thread_manager.save_message(
                db, 
                thread_id=thread_id, 
                role="user", 
                content=last_user.content
            )

        if last_ai:
            await self.thread_manager.save_message(
                db, 
                thread_id=thread_id, 
                role="assistant", 
                content=last_ai.content
            )

        return state
    

# from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
# from langchain_core.messages.utils import trim_messages

# class GraphNode:
#     # 8,000 Token Model Configuration
#     TOTAL_LIMIT = 8000
#     RESPONSE_RESERVE = 1500  # Room for the AI to talk
#     CONTEXT_BUDGET = 2500    # Profile + Summary + Facts
#     HISTORY_BUDGET = 4000    # (TOTAL - RESERVE - CONTEXT)

#     def count_tokens(self, messages):
#         """Standard 1:4 ratio for quick, safe calculation."""
#         if isinstance(messages, str):
#             return len(messages) // 4
#         total_chars = sum(len(str(m.content)) for m in messages if hasattr(m, 'content'))
#         return total_chars // 4

#     async def prepare_context(self, state: ChatState, config):
#         """Runs ONCE at the start of the graph."""
#         # 1. Fetch from DB/Store (Simplified for brevity)
#         profile = "User prefers concise answers." 
#         facts = "User is located in New York."
#         summary = state.get("summary", "")

#         context_str = f"SUMMARY: {summary}\nPROFILE: {profile}\nFACTS: {facts}"
        
#         # 2. Hard character cap to ensure it stays within 2500 tokens
#         char_cap = self.CONTEXT_BUDGET * 4
#         if len(context_str) > char_cap:
#             context_str = context_str[:char_cap] + "...[Truncated]"

#         return {"llm_input": context_str}

#     async def chat_llm(self, state: ChatState, *, config):
#         """The Loop Node: Handles Inference and History Management."""
        
#         # 1. Retrieve the static context prepared earlier
#         dynamic_context = state.get("llm_input", "")

#         # 2. Filter History
#         # We REMOVE any SystemMessages from the message list. 
#         # This prevents 'System Message Stacking' if the tool loops multiple times.
#         clean_history = [m for m in state["messages"] if not isinstance(m, SystemMessage)]

#         # 3. Trim History to 4,000 tokens
#         # Strategy 'last' ensures the most recent Tool results and Human questions stay.
#         trimmed_history = trim_messages(
#             clean_history,
#             max_tokens=self.HISTORY_BUDGET,
#             strategy="last",
#             token_counter=self.count_tokens
#         )

#         # 4. Construct the Final Payload
#         # We 'sandwich' the static context as a SystemMessage at the top.
#         final_payload = []
#         if dynamic_context:
#             final_payload.append(SystemMessage(content=f"INSTRUCTIONS/CONTEXT:\n{dynamic_context}"))
        
#         final_payload.extend(trimmed_history)

#         # 5. Invoke LLM (Math check: 2500 context + 4000 history = 6500. 1500 remains for reply.)
#         response = await self.llm_with_tools.ainvoke({"messages": final_payload})
#         return {"messages": [response]}

#     async def summarize(self, state: ChatState):
#         """Triggers only if history gets too long (e.g. > 4500 tokens)."""
#         # Logic to condense old messages and update state['summary']
#         # This keeps the 'clean_history' in chat_llm from getting truncated too aggressively.
#         pass


    
# Final "Checklist" for your 8k Model:
# Summarize Trigger: 4,000 tokens.

# Summarize Result: 400 tokens.

# Dynamic Context Cap: 2,000 tokens (in prepare_context).

# Chat History Budget: 4,000 tokens (in chat_llm).

# Safety Margin: 1,500 tokens (reserved for generation).