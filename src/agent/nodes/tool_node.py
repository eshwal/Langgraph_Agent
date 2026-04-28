from langgraph.prebuilt.tool_node import ToolNode

class CustomToolNode:

    def __init__(self,tools):
        self.tools = tools
        self.tool_node = None

    def get_tool_node(self):
        if self.tool_node is None:
            self.tool_node = ToolNode(self.tools,handle_tool_errors=True)
        return self.tool_node
    
    def refresh(self):
        """If tools changed or you want a clean node."""
        self.tool_node = None