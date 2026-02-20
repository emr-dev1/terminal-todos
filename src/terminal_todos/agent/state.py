"""Agent state definition for LangGraph."""

from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for the todo agent."""

    # Conversation messages (automatically handles message accumulation)
    messages: Annotated[Sequence[BaseMessage], add_messages]
