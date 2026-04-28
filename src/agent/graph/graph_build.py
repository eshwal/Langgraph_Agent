from langgraph.graph import StateGraph, START, END
from src.agent.state.chatstate import ChatState
from src.agent.nodes.graph_node import GraphNode
from src.agent.nodes.tool_node import CustomToolNode
import logging

logger = logging.getLogger(__name__)

class GraphBuilder:

    def __init__(self,llm,llm_with_tools,tools):
        self.graph=StateGraph(ChatState)
        self.llm = llm
        self.llm_with_tools=llm_with_tools
        self.graph_node = GraphNode(llm,llm_with_tools)
        self.tool_node = CustomToolNode(tools).get_tool_node()
        self._built = False

  
    def build_graph_tools(self):
        # Adding Nodes
        if self._built:
            logger.debug("Graph already built; skipping")
            return
        
        # # Basic validation
        # assert hasattr(self.graph_node, "chat"), "GraphNode must implement chat(state,*,config)"
        # assert hasattr(self.graph_node, "check_tool_end"), "GraphNode must implement check_tool_end"
        # assert hasattr(self.graph_node, "increment_counter"), "GraphNode must implement increment_counter"
        # assert hasattr(self.graph_node, "end_chat"), "GraphNode must implement end_chat"

        self.graph.add_node("chat", self.graph_node.chat_llm)
        self.graph.add_node("tools", self.tool_node)
        self.graph.add_node("increment", self.graph_node.increment_counter)
        self.graph.add_node("end_chat", self.graph_node.end_chat)

        self.graph.add_node("summarize", self.graph_node.summarize)
        self.graph.add_node("prepare_context", self.graph_node.prepare_context) # Added this
        self.graph.add_node("persist", self.graph_node.persist_chat)
      

        # 2. Logic Flow
        # First, decide if we need to summarize
        self.graph.add_conditional_edges(
            START,
            self.graph_node.should_summarize,
            {
                "summarize": "summarize",
                "chat": "prepare_context" # Direct to prepare_context if no summary needed
            }
        )

        # After summarization, we still need to prepare context for the current turn
        self.graph.add_edge("summarize", "prepare_context")

        # After preparing context (filling llm_input), go to chat
        self.graph.add_edge("prepare_context", "chat")

        # 3. The Tool Loop & Exit
        self.graph.add_conditional_edges(
            "chat",
            self.graph_node.check_tool_end, # Ensure this matches your method name
            {
                "end_chat": "end_chat",
                "increment": "increment",
                "persist": "persist"
            }
        )

        
        self.graph.add_edge("increment", "tools")
        self.graph.add_edge("tools", "chat")# Loop back to chat

        # 4. Final Convergence
        self.graph.add_edge("end_chat", "persist") # Save summarized fallback
        self.graph.add_edge("persist", END)        # Final exit
        self._built = True
        logger.info("Graph built successfully with chat/tools loop")

    def get_graph_tools(self):
        if not self._built:
            # optional: auto-build when calling getter
            self.build_graph_tools()
        return self.graph

    