# import uuid
# import logging
# from langchain_core.messages import SystemMessage
# from src.schemas.memory import MemoryExtraction

# logger = logging.getLogger(__name__)

# async def store_long_term_pref(state, store, llm, user_id):
#     """
#     Background task to extract and persist user memories.
#     Runs every turn but filters for meaningful content.
#     """
#     messages = state.get("messages", [])
    
#     # --- GATEKEEPER: Industry Best Practice ---
#     # 1. Don't process if the conversation just started
#     if len(messages) < 2:
#         return
    
#     # 2. Don't process if the last message is very short (e.g., "Thanks", "Ok")
#     if len(messages[-1].content.strip()) < 5:
#         return

#     logger.debug(f"Extracting memory for user: {user_id}")

#     # --- SETUP CONTEXT ---
#     namespace = ("memories", user_id)
#     current_summary = state.get("summary", "No prior summary.")
#     context_window = messages[-6:]  # The last 3 turns (User + AI)

#     reflection_prompt = """
#     Extract PERSISTENT facts about the user or their project.
    
#     CATEGORIES:
#     - 'user_profile': Identity (Name, Job, Role, Location).
#     - 'user_preferences': Habits or likes (e.g., 'prefers Python').
#     - 'project_context': Details about the specific project they are building.

#     STRICT RULES:
#     1. DO NOT extract general definitions (e.g., ignore what a WebSocket is).
#     2. ONLY extract technical info if it's about the user's specific app/work.
#     3. If no new facts are found, return an empty list.
#     """

#     # Combine summary and messages for extraction
#     extraction_input = [
#         SystemMessage(content=reflection_prompt),
#         SystemMessage(content=f"Current Context Summary: {current_summary}")
#     ] + context_window

#     # --- LLM INVOCATION WITH RETRY ---
#     extractor = llm.with_structured_output(MemoryExtraction)
#     extracted = None

#     try:
#         extracted = await extractor.ainvoke(extraction_input)
#     except Exception as e:
#         logger.error(f"Memory extraction failed on first attempt: {e}")
#         # Simple retry logic could go here if needed
#         return

#     if not extracted or not extracted.facts:
#         return

#     # # --- PERSISTENCE LOGIC ---
#     # for fact in extracted.facts:
#     #     # CATEGORY 1: User Profile (The "Bio" Singleton)
#     #     if fact.topic == MemoryCategory.user_profile:
#     #         existing_profile = await store.aget(namespace, "core_profile")
#     #         if existing_profile:
#     #             merge_prompt = (
#     #                 f"Existing Profile: {existing_profile.value['content']}\n"
#     #                 f"New Detail: {fact.content}\n"
#     #                 "Update the bio to include all details. Keep it concise."
#     #             )
#     #             merged = await llm.ainvoke(merge_prompt)
#     #             await store.aput(namespace, "core_profile", {"content": merged.content})
#     #         else:
#     #             await store.aput(namespace, "core_profile", {"content": fact.content})
#     #         continue

#     #     # CATEGORY 2 & 3: Semantic Upsert (Deduplication)
#     #     # Search for similar existing facts to avoid duplicates
#     #     existing = await store.asearch(namespace, query=fact.content, limit=1)
        
#     #     # If it's a direct update, be more lenient on matching (0.7)
#     #     threshold = 0.70 if fact.is_update else 0.85
        
#     #     if existing and existing[0].score > threshold:
#     #         # Update existing record
#     #         await store.aput(namespace, existing[0].key, fact.model_dump())
#     #     else:
#     #         # Create a brand new record with a unique ID
#     #         await store.aput(namespace, str(uuid.uuid4()), fact.model_dump())

#     # logger.info(f"Successfully stored {len(extracted.facts)} facts for {user_id}")


#     for fact in extracted.facts:
#     # --- BLOCK 1: STRICT PROFILE LOGIC ---
#         if fact.topic == "user_profile":
#             logger.info("Saving to core_profile...")
#             existing_profile = await store.aget(namespace, "core_profile")
            
#             if existing_profile:
#                 merge_prompt = f"Merge: {existing_profile.value['content']} with {fact.content}"
#                 merged = await llm.ainvoke(merge_prompt)
#                 await store.aput(namespace, "core_profile", {"content": merged.content})
#             else:
#                 await store.aput(namespace, "core_profile", {"content": fact.content})
            
#             continue # 👈 ESSENTIAL: Move to next fact, do not run code below

#         # --- BLOCK 2: EVERYTHING ELSE ---
#         # We only reach here if topic is NOT user_profile
#         existing = await store.asearch(namespace, query=fact.content, limit=5)
        
#         # Filter out 'core_profile' just in case the vector search is being "helpful"
#         potential_matches = [e for e in existing if e.key != "core_profile"]
        
#         best_match = potential_matches[0] if potential_matches else None
#         threshold = 0.70 if fact.is_update else 0.85

#         if best_match and best_match.score > threshold:
#             await store.aput(namespace, best_match.key, fact.model_dump())
#         else:
#             # This MUST result in a UUID key
#             new_key = str(uuid.uuid4())
#             await store.aput(namespace, new_key, fact.model_dump())
#             logger.info(f"Created new technical memory with key: {new_key}")


# import uuid
# import logging
# import re
# from langchain_core.messages import SystemMessage
# from src.schemas.memory import MemoryExtraction, MemoryCategory

# logger = logging.getLogger(__name__)

# async def store_long_term_pref(state, store, llm, user_id):
#     messages = state.get("messages", [])
    
#     # --- 1. GATEKEEPER: Avoid wasting tokens on small talk ---
#     if len(messages) < 2 or len(messages[-1].content.strip()) < 5:
#         return

#     # --- 2. SETUP CONTEXT ---
#     namespace = ("memories", user_id)
#     current_summary = state.get("summary", "No prior summary.")
#     context_window = messages[-6:] 

#     reflection_prompt = """
#     Extract PERSISTENT facts about the user which can be later used for personalized responses.

#     CATEGORIES:
#      - 'user_profile': Identity (Name, Job, Role, Location).
#      - 'user_preferences': Habits or likes (e.g., 'prefers Python').
#      - 'project_context': Details about the specific project they are building.
    
#     STRICT RULES:
#     1. 'is_explicit': Set to True ONLY if the user makes a statement about themselves. 
#        (e.g., "I like Python" -> True | "How does Python work?" -> False).
#     2. DO NOT extract general knowledge or definitions.
#     3. If the user corrects a previous fact, set is_update=True.
#     4. Always extract facts which can be used for long term 
#     5. Be careful and extract correctly as per category . Don't merge or confuse with categories(e.g user_profile should not contain user_preferences or project_context.)
#     """

#     extraction_input = [
#         SystemMessage(content=reflection_prompt),
#         SystemMessage(content=f"Current Context Summary: {current_summary}")
#     ] + context_window

#     extractor = llm.with_structured_output(MemoryExtraction)
#     try:
#         extracted = await extractor.ainvoke(extraction_input)
#     except Exception as e:
#         logger.error(f"Extraction failed: {e}")
#         return

#     if not extracted or not extracted.facts:
#         return

#     # --- 3. PROCESSING LOOP ---
#     for fact in extracted.facts:
#         # Stop "Curiosity" spam: Only save if the user explicitly stated it
#         if not fact.is_explicit:
#             continue

#         # CATEGORY 1: User Profile (The Bio)
#         if fact.topic == MemoryCategory.user_profile:
#             existing_profile = await store.aget(namespace, "core_profile")
#             if existing_profile:
#                 merge_prompt = (
#             f"Existing Profile: {existing_profile.value['content']}\n"
#             f"New Detail: {fact.content}\n"
#             "Combine these into a single profile. "
#             "IMPORTANT: Never remove the user's name if it is already known."
#             )
#                 merged = await llm.ainvoke(merge_prompt)
#                 await store.aput(namespace, "core_profile", {"content": merged.content})
#             else:
#                 await store.aput(namespace, "core_profile", {"content": fact.content})
#             continue

#         # CATEGORY 2 & 3: Preferences & Project (The LLM Judge)
#         # Search for similar items to see if we should update or create new
#         search_results = await store.asearch(namespace, query=fact.content, limit=3)
        
#         # Isolation: Ensure we don't compare technical facts against the Bio
#         candidates = [m for m in search_results if m.key != "core_profile"]

#         if not candidates:
#             await store.aput(namespace, str(uuid.uuid4()), fact.model_dump())
#         else:
#             # The Judge decides if this is a DUPLICATE, an UPDATE, or NEW
#             memory_list = "\n".join([f"ID: {m.key} | Content: {m.value['content']}" for m in candidates])
#             judge_prompt = f"""
#             New Fact: "{fact.content}"
#             Existing Memories:
#             {memory_list}

#             Instructions:
#             1. If the New Fact updates, corrects, or is the same as an existing ID, return ONLY that ID.
#             2. If it is a completely different fact, return 'NEW'.
#             3. Return only the ID or 'NEW', nothing else.
#             """
            
#             decision = await llm.ainvoke(judge_prompt)
#             decision_text = decision.content.strip()

#             # Robust ID extraction (regex handles if LLM adds extra text)
#             match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', decision_text)
            
#             if "NEW" in decision_text.upper() or not match:
#                 await store.aput(namespace, str(uuid.uuid4()), fact.model_dump())
#             else:
#                 target_key = match.group(0)
#                 await store.aput(namespace, target_key, fact.model_dump())


import uuid
import logging
import re
from langchain.messages import SystemMessage,HumanMessage,AIMessage
from src.schemas.memory import MemoryExtraction, MemoryCategory

logger = logging.getLogger(__name__)

# async def store_long_term_pref(state, store, llm, user_id):
#     messages = state.get("messages", [])
#     if len(messages) < 2:
#         return

#     namespace = ("memories", user_id)
    
#     reflection_prompt = """
#     You are a Memory Manager. Your job is to extract LONG-TERM facts.
    
#     STRICT RULES:
#     1. USER_IDENTITY: Name, Job Title, or Role (e.g., 'My name is Alex', 'I am a Lead Dev').
#     2. USER_PREFERENCES: Permanent tool choices or styles (e.g., 'I prefer async code').
#     3. PROJECT_GOAL: The 'North Star' of the project (e.g., 'Building a memory-enabled chatbot').
    
#     IGNORE: 
#     - Transient bugs: 'I have an error in my code', 'I'm stuck on this import'.
#     - Small talk: 'I'm feeling good', 'Thanks for the help'.
#     - Questions: 'How do I use this?' is NOT a preference.
    
#     SIGNIFICANCE SCORING:
#     - 5: Name, Role, Core Project Goal.
#     - 3: Tech stack preferences.
#     - 1: Current debugging issues or temporary tasks (DO NOT EXTRACT).
#     """

#     extractor = llm.with_structured_output(MemoryExtraction)
#     try:
#         # We only look at the last few messages to find new facts
#         extracted = await extractor.ainvoke([
#             ("system", reflection_prompt),
#             *messages[-4:] 
#         ])
#     except Exception as e:
#         logger.error(f"Extraction failed: {e}")
#         return

#     if not extracted or not extracted.facts:
#         return

#     for fact in extracted.facts:
#         # Filter: Only keep explicit statements and high-value info
#         if not fact.is_explicit or fact.significance < 3:
#             continue

#         # --- SPECIAL HANDLING: USER IDENTITY (THE BIO) ---
#         if fact.topic == MemoryCategory.user_identity:
#             existing_profile = await store.aget(namespace, "core_profile")
            
#             if existing_profile:
#                 # Merge logic to ensure Name/Role is never overwritten by "I am working on..."
#                 merge_prompt = f"""
#                 Existing Identity: {existing_profile.value['content']}
#                 New Identity Info: {fact.content}
                
#                 Combine into a single concise bio. 
#                 CRITICAL: If the name or primary role is in the existing identity, DO NOT remove it.
#                 """
#                 merged = await llm.ainvoke(merge_prompt)
#                 await store.aput(namespace, "core_profile", {"content": merged.content.strip()})
#             else:
#                 await store.aput(namespace, "core_profile", {"content": fact.content})
#             continue

#         # --- HANDLING PREFERENCES & PROJECT GOALS ---
#         # Search for existing similar memories to avoid duplicates
#         search_results = await store.asearch(namespace, query=fact.content, limit=3)
#         candidates = [m for m in search_results if m.key != "core_profile"]

#         if not candidates:
#             await store.aput(namespace, str(uuid.uuid4()), fact.model_dump())
#         else:
#             # The Judge: Is this NEW, an UPDATE, or a DUPLICATE?
#             memory_list = "\n".join([f"ID: {m.key} | Content: {m.value['content']}" for m in candidates])
#             judge_prompt = f"""
#             New Fact: "{fact.content}"
#             Existing Memories: {memory_list}
            
#             Instructions:
#             - If it updates/corrects an ID, return ONLY that ID.
#             - If it's a duplicate of an existing ID, return ONLY that ID.
#             - If it's completely new, return 'NEW'.
#             """
#             decision = await llm.ainvoke(judge_prompt)
#             decision_text = decision.content.strip()

#             match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', decision_text)
            
#             if "NEW" in decision_text.upper() or not match:
#                 await store.aput(namespace, str(uuid.uuid4()), fact.model_dump())
#             else:
#                 # Overwrite the old memory with the updated/confirmed fact
#                 await store.aput(namespace, match.group(0), fact.model_dump())


import re
import uuid
import logging
# from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# async def store_long_term_pref(state, store, llm, user_id):
#     messages = state.get("messages", [])
#     if not messages:
#         return

#     namespace = ("memories", user_id)
#     existing_profile = await store.aget(namespace, "core_profile")
    
#     # --- STEP 1: CLEANING LOGIC ---
#     cleaned_messages = []
#     for m in messages:
#         if m.type == "tool" or (hasattr(m, "tool_calls") and m.tool_calls):
#             continue
        
#         # Strip XML and artifacts to prevent LLM confusion
#         new_content = re.sub(r'<.*?>.*?</.*?>', '', m.content, flags=re.DOTALL)
#         new_content = re.sub(r'<.*?>', '', new_content).strip()
        
#         if new_content:
#             msg_class = HumanMessage if isinstance(m, HumanMessage) else AIMessage
#             cleaned_messages.append(msg_class(content=new_content))

#     context_to_analyze = cleaned_messages if not existing_profile else cleaned_messages[-4:]

#     # --- STEP 2: THE PROMPT (With One-Shot Example) ---
#     reflection_prompt = f"""
#     You are a Memory Observer. Extract PERMANENT facts about the HUMAN USER from the dialogue.
    
#     CATEGORIES: 'user_identity', 'user_preferences', 'project_goal'.
    
#     EXAMPLE OUTPUT:
#     {{
#       "facts": [
#         {{
#           "topic": "user_identity",
#           "content": "The user is a Senior Dev based in Berlin.",
#           "is_update": false,
#           "is_explicit": true,
#           "significance": 5
#         }}
#       ]
#     }}

#     CRITICAL: Do NOT extract info about the AI. Only extract facts about the human.
#     """

#     # --- STEP 3: EXTRACTION ---
#     # We use .with_structured_output but explicitly handle the response
#     extractor = llm.with_structured_output(MemoryExtraction)
    
#     try:
#         extracted = await extractor.ainvoke([
#             SystemMessage(content=reflection_prompt),
#             *context_to_analyze
#         ])
#     except Exception as e:
#         logging.error(f"Structured extraction 400 Error: {e}")
#         return

#     if not extracted or not extracted.facts:
#         return

#     # --- STEP 4: VALIDATION & STORAGE ---
#     for fact in extracted.facts:
#         # 1. Manual validation of significance and explicitness
#         if not fact.is_explicit or int(fact.significance) < 3:
#             continue
            
#         # 2. Ensure topic is valid (failsafe for hallucinated enums)
#         if fact.topic not in [c.value for c in MemoryCategory]:
#             continue

#         # Handle Identity (Bio)
#         if fact.topic == MemoryCategory.user_identity.value:
#             if existing_profile:
#                 merge_prompt = f"Existing Bio: {existing_profile.value['content']}\nNew Info: {fact.content}\nCombine into one concise bio sentence."
#                 merged = await llm.ainvoke(merge_prompt)
#                 await store.aput(namespace, "core_profile", {"content": merged.content.strip()})
#             else:
#                 await store.aput(namespace, "core_profile", {"content": fact.content})
#             continue

#         # Handle General Preferences/Goals with Deduplication
#         search_results = await store.asearch(namespace, query=fact.content, limit=3)
#         candidates = [m for m in search_results if m.key != "core_profile"]

#         if not candidates:
#             await store.aput(namespace, str(uuid.uuid4()), fact.model_dump())
#         else:
#             # Judge if we update or ignore
#             memory_list = "\n".join([f"ID: {m.key} | {m.value['content']}" for m in candidates])
#             judge_prompt = f"New: {fact.content}\nOld:\n{memory_list}\nUpdate which ID? (Return ID or 'NEW')"
#             decision = await llm.ainvoke(judge_prompt)
            
#             match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', decision.content)
#             if match:
#                 await store.aput(namespace, match.group(0), fact.model_dump())
#             elif "NEW" in decision.content.upper():
#                 await store.aput(namespace, str(uuid.uuid4()), fact.model_dump())


# from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
# from langchain_core.output_parsers import PydanticOutputParser

# async def store_long_term_pref(state, store, llm, user_id):
#     messages = state.get("messages", [])
#     if not messages:
#         return

#     namespace = ("memories", user_id)
#     existing_profile = await store.aget(namespace, "core_profile")
    
#     # --- 1. CLEAN CONTEXT ---
#     cleaned_messages = []
#     for m in messages:
#         if m.type == "tool" or (hasattr(m, "tool_calls") and m.tool_calls):
#             continue
#         # Remove tags and artifacts
#         txt = re.sub(r'<.*?>.*?</.*?>', '', m.content, flags=re.DOTALL)
#         txt = re.sub(r'<.*?>', '', txt).strip()
#         if txt:
#             cleaned_messages.append(HumanMessage(content=txt) if isinstance(m, HumanMessage) else AIMessage(content=txt))

#     context_to_analyze = cleaned_messages if not existing_profile else cleaned_messages[-6:]

#     # --- 2. SETUP PARSER & PROMPT ---
#     parser = PydanticOutputParser(pydantic_object=MemoryExtraction)
    
#     reflection_prompt = f"""
#     You are a Memory Observer. Your task is to extract PERMANENT facts about the user.

#     ### EXAMPLES of EXTRACTION:

#     1. [USER IDENTITY]
#     Input: "My name is Aisha and I've been a dev for 5 years."
#     Output: {{ "facts": [{{ "topic": "user_identity", "content": "The user's name is Aisha and she is a software developer.", "is_update": false, "is_explicit": true, "significance": 5 }}] }}

#     2. [USER PREFERENCES]
#     Input: "I really prefer using tailwind for my styling, I hate bootstrap."
#     Output: {{ "facts": [{{ "topic": "user_preferences", "content": "The user prefers Tailwind CSS over Bootstrap for styling.", "is_update": false, "is_explicit": true, "significance": 4 }}] }}

#     3. [PROJECT GOALS]
#     Input: "I'm currently trying to launch a new SaaS for pet groomers."
#     Output: {{ "facts": [{{ "topic": "project_goal", "content": "The user is building a SaaS platform for pet groomers.", "is_update": false, "is_explicit": true, "significance": 5 }}] }}
        
#     {parser.get_format_instructions()}
    
#     CATEGORIES:
#     - user_identity: Name, Role, Location.
#     - user_preferences: Likes/Dislikes, tech stack.
#     - project_goal: What the user is currently building.
    
#     IGNORE: 
#     - Transient bugs: 'I have an error in my code', 'I'm stuck on this import'.
#     - Small talk: 'I'm feeling good', 'Thanks for the help'.
#     - Questions: 'How do I use this?' or 'What is AI' is NOT a preference.

#     STRICT RULES:
#     - Return ONLY the JSON object. No markdown code blocks.
#     - IGNORE the AI. ONLY extract facts about the HUMAN or current user.
#     - If no new facts are found in the recent messages, return {{ "facts": [] }}.
#     """
#     # --- 3. ROBUST EXTRACTION ---
#     try:
#         # We call the LLM directly, NOT using with_structured_output
#         response = await llm.ainvoke([
#             SystemMessage(content=reflection_prompt),
#             *context_to_analyze
#         ])
        
#         raw_text = response.content
        
#         # CLEANING LLAMA OUTPUT: Remove markdown backticks if present
#         clean_json = re.sub(r'```json\s?|\s?```', '', raw_text).strip()
        
#         # Find the first '{' and last '}' in case of extra text
#         start_idx = clean_json.find('{')
#         end_idx = clean_json.rfind('}')
#         if start_idx != -1 and end_idx != -1:
#             clean_json = clean_json[start_idx:end_idx+1]
            
#         extracted = parser.parse(clean_json)
#     except Exception as e:
#         logging.error(f"Llama-8b Parsing Failed: {e}. Raw: {raw_text[:100]}")
#         return

#     # --- 4. STORAGE & DEDUPLICATION ---
#     if not extracted.facts:
#         return

#     for fact in extracted.facts:
#         # Only save significant, explicit facts
#         if not fact.is_explicit or fact.significance < 3:
#             continue
            
#         # Topic Failsafe
#         if fact.topic not in [c.value for c in MemoryCategory]:
#             continue

#         # Logic for Core Profile (Identity)
#         if fact.topic == MemoryCategory.user_identity.value:
#             if existing_profile:
#                 merge_res = await llm.ainvoke(f"Combine into one bio: '{existing_profile.value['content']}' + '{fact.content}'")
#                 await store.aput(namespace, "core_profile", {"content": merge_res.content.strip()})
#             else:
#                 await store.aput(namespace, "core_profile", {"content": fact.content})
#             continue

#         # Logic for deduplicating other memories
#         search_results = await store.asearch(namespace, query=fact.content, limit=2)
#         candidates = [m for m in search_results if m.key != "core_profile"]

#         if not candidates:
#             await store.aput(namespace, str(uuid.uuid4()), fact.model_dump())
#         else:
#             # Check if this is an update or a duplicate
#             mem_str = "\n".join([f"ID: {m.key} | {m.value['content']}" for m in candidates])
#             decision = await llm.ainvoke(f"New: {fact.content}\nOld:\n{mem_str}\nUpdate which ID? (Return ID or 'NEW')")
            
#             match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', decision.content)
#             if match:
#                 await store.aput(namespace, match.group(0), fact.model_dump())
#             elif "NEW" in decision.content.upper():
#                 await store.aput(namespace, str(uuid.uuid4()), fact.model_dump())

async def store_long_term_pref(state, store, llm, user_id):
    messages = state.get("messages", [])
    if not messages: return

    namespace = ("memories", user_id)
    
    # 1. Focus only on the most recent exchange to avoid redundant processing
    # We look at the last N messages since we only trigger every MESSAGE_THRESHOLD
    context_to_analyze = messages[-8:] 

    # 2. Force Single-Sentence Extraction
    # Using with_structured_output is much more reliable than manual regex cleaning
    structured_llm = llm.with_structured_output(MemoryExtraction)
    
    reflection_prompt = f"""
    You are a Memory Observer. Your task is to extract PERMANENT facts about the user.

    ### EXAMPLES of EXTRACTION:

    1. [USER IDENTITY]
    Input: "My name is Aisha and I've been a dev for 5 years."
    Output: {{ "facts": [{{ "topic": "user_identity", "content": "The user's name is Aisha and she is a software developer.", "is_update": false, "is_explicit": true, "significance": 5 }}] }}

    2. [USER PREFERENCES]
    Input: "I really prefer using tailwind for my styling, I hate bootstrap."
    Output: {{ "facts": [{{ "topic": "user_preferences", "content": "The user prefers Tailwind CSS over Bootstrap for styling.", "is_update": false, "is_explicit": true, "significance": 4 }}] }}

    3. [PROJECT GOALS]
    Input: "I'm currently trying to launch a new SaaS for pet groomers."
    Output: {{ "facts": [{{ "topic": "project_goal", "content": "The user is building a SaaS platform for pet groomers.", "is_update": false, "is_explicit": true, "significance": 5 }}] }}
        
    
    CATEGORIES:
    - user_identity: Name, Role, Location.
    - user_preferences: Likes/Dislikes, tech stack.
    - project_goal: What the user is currently building.
    
    IGNORE: 
    - Transient bugs: 'I have an error in my code', 'I'm stuck on this import'.
    - Small talk: 'I'm feeling good', 'Thanks for the help'.
    - Questions: 'How do I use this?' or 'What is AI' is NOT a preference.

    STRICT RULES:
    - Each fact MUST be a single, concise sentence (max 12 words).
    - Use present tense (e.g., "User prefers Python").
    - IGNORE the AI. ONLY extract facts about the HUMAN or current user.
    - If no new facts are found in the recent messages, return {{ "facts": [] }}.
    """

    try:
        extracted = await structured_llm.ainvoke([
            SystemMessage(content=reflection_prompt),
            *context_to_analyze
        ])
    except Exception as e:
        logging.error(f"Extraction failed: {e}")
        return

    if not extracted or not extracted.facts:
        return

    for fact in extracted.facts:
        if fact.significance < 3: continue

        # 3. Smart Deduplication using Vector Search
        # We search for existing facts that are semantically similar
        existing = await store.asearch(namespace, query=fact.content, limit=1)
        
        if existing:
            # check similarity score (LangGraph store returns score in metadata/search results)
            # If it's a very high match, it's a duplicate or a slight update
            # We use a simple threshold or a quick LLM "is_same" check
            top_match = existing[0]
            
            # Logic: If it's the same topic and highly similar, just overwrite the old one
            # to keep the "latest" version of that fact/preference.
            await store.aput(namespace, top_match.key, fact.model_dump())
        else:
            # Truly new information
            await store.aput(namespace, str(uuid.uuid4()), fact.model_dump())