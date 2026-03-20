"""LangGraph CLI entry point - exposes the agent for `langgraph dev`."""

from ai_app.agent.graph import get_agent

# Expose the compiled graph for langgraph dev
agent = get_agent()
