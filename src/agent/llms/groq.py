from langchain_groq import ChatGroq


class GroqLLM:

    def __init__(self,model:str,api_key:str):
        self.model = model
        if not api_key:
            raise ValueError("Missing Groq API key")
        else:
            self.api_key = api_key
        self._llm = None


    def get_llm(self):
        '''Retrun llm'''
        if self._llm is None:
            model = self.model
            groq_api_key = self.api_key
            self._llm = ChatGroq(model=model,groq_api_key=groq_api_key)
        return self._llm
    

    def get_llm_with_tools(self,tools:list):
        '''Return llm with tools'''
        return self.get_llm().bind_tools(tools)
