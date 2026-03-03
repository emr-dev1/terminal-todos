"""WebSocket endpoint for streaming LangGraph agent chat."""

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter(tags=["chat"])

# Tools that mutate todos — triggers a refresh signal to the frontend
TODO_MUTATING_TOOLS = {
    "create_todo",
    "complete_todo",
    "uncomplete_todo",
    "update_todo",
    "delete_todo",
    "delete_todos_bulk",
    "add_to_focus",
    "remove_from_focus",
    "clear_focus_list",
    "label_todo",
}


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    await websocket.accept()

    # Each connection gets its own message history
    message_history: list[Any] = []

    try:
        from terminal_todos.agent.graph import get_agent_graph
        graph = get_agent_graph()
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"Failed to initialize agent: {e}"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                user_text = payload.get("message", "").strip()
            except (json.JSONDecodeError, AttributeError):
                await websocket.send_json({"type": "error", "message": "Invalid message format"})
                continue

            if not user_text:
                continue

            message_history.append(HumanMessage(content=user_text))

            # Accumulate the final AI response text for history
            final_content = ""
            tools_called: set[str] = set()
            refresh_needed = False

            try:
                async for event in graph.astream_events(
                    {"messages": message_history},
                    version="v2",
                ):
                    kind = event.get("event", "")
                    name = event.get("name", "")

                    if kind == "on_chat_model_stream":
                        chunk = event["data"].get("chunk")
                        if chunk and chunk.content:
                            token = chunk.content
                            final_content += token
                            await websocket.send_json({"type": "token", "content": token})

                    elif kind == "on_tool_start":
                        tools_called.add(name)
                        await websocket.send_json({"type": "tool_start", "tool": name})
                        if name in TODO_MUTATING_TOOLS:
                            refresh_needed = True

                    elif kind == "on_tool_end":
                        await websocket.send_json({"type": "tool_end", "tool": name})

            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})
                continue

            # Append assistant response to history
            if final_content:
                message_history.append(AIMessage(content=final_content))

            if refresh_needed:
                await websocket.send_json({"type": "refresh_todos"})

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
