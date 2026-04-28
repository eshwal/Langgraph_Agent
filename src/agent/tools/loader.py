from src.agent.tools.tool import CustomTool

def load_tools():
    custom_tool = CustomTool()
    custom_tool.get_duck_duck_go(add=True)
    custom_tool.get_wiki(add=True)
    tools = custom_tool.get_tools()
    return tools