"""LangGraph agent graph definition."""

from typing import Optional
import os

from langgraph.graph import StateGraph, END

from terminal_todos.agent.nodes import create_agent_node, should_continue, tool_node
from terminal_todos.agent.state import AgentState
from terminal_todos.agent.tools import init_tools
from terminal_todos.config import get_settings
from terminal_todos.core.note_service import NoteService
from terminal_todos.core.todo_service import TodoService


# Global flag to track if Arize tracing has been initialized
_arize_initialized = False


def _initialize_arize_tracing():
    """Initialize Arize tracing if enabled and not already initialized."""
    global _arize_initialized

    if _arize_initialized:
        return

    settings = get_settings()

    if settings.enable_arize_tracing:
        try:
            # Set environment variables for Arize credentials
            if settings.arize_space_id:
                os.environ["ARIZE_SPACE_ID"] = settings.arize_space_id
            if settings.arize_api_key:
                os.environ["ARIZE_API_KEY"] = settings.arize_api_key

            # Import Arize instrumentation
            from arize.otel import register
            from openinference.instrumentation.langchain import LangChainInstrumentor

            # Setup OTel via Arize's convenience function
            tracer_provider = register(
                space_id=os.getenv("ARIZE_SPACE_ID"),
                api_key=os.getenv("ARIZE_API_KEY"),
                project_name=settings.arize_project_name
            )

            # Instrument LangChain (which includes LangGraph)
            LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

            _arize_initialized = True

            print("✓ Arize tracing initialized")
            print(f"  Project: {settings.arize_project_name}")
            print(f"  Space ID: {settings.arize_space_id[:8]}..." if settings.arize_space_id else "  Space ID: Not set")

        except Exception as e:
            print(f"⚠ Failed to initialize Arize tracing: {e}")
            print("  Agent will continue without tracing")


def create_agent_graph(
    llm_model: Optional[str] = None, api_key: Optional[str] = None
):
    """
    Create the agent graph with optional Arize tracing.

    Args:
        llm_model: Optional LLM model override
        api_key: Optional API key override

    Returns:
        Compiled LangGraph with tracing enabled (if configured)
    """
    # Initialize Arize tracing (only once globally)
    _initialize_arize_tracing()

    # Initialize services for tools
    todo_service = TodoService()
    note_service = NoteService()
    init_tools(todo_service, note_service)

    # Create the agent node
    agent_node = create_agent_node(llm_model=llm_model, api_key=api_key)

    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Compile the graph
    return workflow.compile()


# Global graph instance
_agent_graph = None


def get_agent_graph():
    """Get or create the global agent graph instance."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = create_agent_graph()
    return _agent_graph


def reset_agent_graph():
    """Reset the global agent graph (for testing)."""
    global _agent_graph
    _agent_graph = None


def reset_arize_tracing():
    """Reset Arize tracing initialization flag (for testing)."""
    global _arize_initialized
    _arize_initialized = False
