from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper, WikipediaAPIWrapper


class CustomTool:
    def __init__(self):
        # Correct way to initialize: creates a fresh list for every new instance
        self.tools = []
        self._duck_tool = None
        self._wiki_tool = None

    def get_duck_duck_go(self, add=False):
        if self._duck_tool is None:
            duck_wrapper = DuckDuckGoSearchAPIWrapper(region="us-en", max_results=2)
            self._duck_tool = DuckDuckGoSearchRun(
                name='web_search', 
                description='Search the web for English results only', 
                api_wrapper=duck_wrapper
            )
        
        if add:
            self.add_tool(self._duck_tool)
            
        return self._duck_tool

    def get_wiki(self, add=False):
        if self._wiki_tool is None:
            wiki_wrapper = WikipediaAPIWrapper(top_k_results=2, lang="en")
            self._wiki_tool = WikipediaQueryRun(
                name='wiki', 
                description='Search Wikipedia', 
                api_wrapper=wiki_wrapper
            )
            
        if add:
            self.add_tool(self._wiki_tool)
            
        return self._wiki_tool

    def add_tool(self, tool):
        # Checking by 'name' attribute is safer than checking by object identity
        if any(t.name == tool.name for t in self.tools):
            return "Tool already exists"
        
        self.tools.append(tool)
        return "Tool added"

    def get_tools(self):
        """Returns the list of tools currently added to this instance."""
        return self.tools