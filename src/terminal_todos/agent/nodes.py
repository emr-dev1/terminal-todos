"""Agent nodes for LangGraph."""

from typing import Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from terminal_todos.agent.prompts import SYSTEM_PROMPT
from terminal_todos.agent.state import AgentState
from terminal_todos.agent.tools import ALL_TOOLS
from terminal_todos.config import get_settings


# Create tool node (handles tool execution)
tool_node = ToolNode(ALL_TOOLS)


def create_agent_node(llm_model: str = None, api_key: str = None):
    """
    Create the agent node function.

    Returns:
        Agent node function
    """
    settings = get_settings()
    model = llm_model or settings.llm_model
    key = api_key or settings.openai_api_key

    # Create LLM with tools
    llm = ChatOpenAI(model=model, api_key=key, temperature=0)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def agent_node(state: AgentState) -> AgentState:
        """
        Agent node that decides what to do next.

        Args:
            state: Current agent state

        Returns:
            Updated state with agent's response
        """
        messages = state["messages"]

        # Add system message if this is the first turn
        if len(messages) == 1:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)

        # Call LLM
        response = llm_with_tools.invoke(messages)

        return {"messages": [response]}

    return agent_node


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    Determine if we should continue to tools or end.

    Args:
        state: Current agent state

    Returns:
        "tools" if agent wants to call tools, "end" otherwise
    """
    messages = state["messages"]
    last_message = messages[-1]

    # If the last message has tool calls, route to tools
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    # Otherwise, end the conversation
    return "end"
