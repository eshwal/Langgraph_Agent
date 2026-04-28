from src.agent.graph.graph_build import GraphBuilder
from src.agent.llms.groq import GroqLLM
from src.agent.tools import loader
from src.agent.prompts.loader import load_prompt
from src.config.settings import settings



def get_graph_with_tools():

    groq_llm = GroqLLM(
        model=settings.MODEL_NAME,
        api_key=settings.GROQ_API_KEY
        )
    
    tools = loader.load_tools()

    llm = groq_llm.get_llm()
    llm_tools = groq_llm.get_llm_with_tools(tools)

    prompt = load_prompt()
    llm_with_tools= prompt| llm_tools
    
    graph_builder = GraphBuilder(llm,llm_with_tools,tools)
    return graph_builder.get_graph_tools()