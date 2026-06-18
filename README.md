# LangGraph Agent

A comprehensive AI agent framework built with [LangGraph](https://github.com/langchain-ai/langgraph) and LangChain, featuring a complete backend implementation and interactive web UI.

## 📋 Overview

This repository contains a production-ready LangGraph agent system that demonstrates how to build stateful, multi-step AI agents with:

- **Graph-based orchestration** - Define complex agent workflows as directed graphs
- **State management** - Maintain context across multi-turn conversations
- **Tool integration** - Extend agent capabilities with custom tools
- **Web UI** - Interactive interface for testing and deploying agents
- **Modular architecture** - Clean separation between core logic and presentation

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- An API key for your chosen LLM provider (OpenAI, Anthropic, etc.)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/eshwal/Langgraph_Agent.git
cd Langgraph_Agent
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Application

#### Backend Only
```bash
python main.py
```

#### With Web UI
```bash
python start_app.py
```

The application will start and be accessible at `http://localhost:8000` (or the configured port).


## 🖥️ Web UI

The UI provides:

- **Chat interface** - Interact with the agent in real-time
- **Message history** - View complete conversation history
- **Tool visualization** - See which tools the agent uses

## 📦 Dependencies

Key dependencies include:

- **langgraph**: Agent orchestration framework
- **langchain**: LLM integrations and utilities
- **langchain-groq**: LLM providers
- **fastapi** or **flask**: Backend 
- **streamlit**: Web framework (if using UI)
- **pydantic**: Data validation


## 🎯 Future Enhancements

Potential improvements for future versions:

- [ ] Multi-agent collaboration
- [ ] Advanced memory systems (long-term, semantic)
- [ ] Human-in-the-loop checkpoints
- [ ] Deployment to cloud platforms (AWS, GCP, Azure)
- [ ] Advanced monitoring and observability
- [ ] Rate limiting and usage tracking
- [ ] Role-based access control
- [ ] Database persistence for conversations

---

**Happy Building! 🚀**

Built with ❤️ using [LangGraph](https://github.com/langchain-ai/langgraph)
