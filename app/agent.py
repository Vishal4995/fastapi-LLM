# app/agent.py
import os
from typing import List, Dict, Callable, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    BaseMessage,
)
from .tools import build_tools
from .orchestrator import make_fast_executor as make_executor

SYSTEM = """You are an HR/IT analytics assistant.
You have access to TOOLS. Use them to answer questions about employees, departments, projects, and attendance.

Rules:
- Choose the most relevant tools with precise parameters.
- You may call multiple tools step-by-step. Stop calling tools once you have enough to answer.
- If results are empty or the question is ambiguous, say so and suggest a better query.
- Do NOT fabricate data. Tools are read-only.
- Give concise answers with key names, counts, and dates where helpful.
"""

def make_executor(db) -> Callable[[Dict[str, Any]], Dict[str, str]]:
    """
    Always returns a callable executor. If initialization fails, returns a
    stub that reports the initialization error in the output instead of crashing.
    """
    try:
        tools = build_tools(db)
        name_to_tool = {t.name: t for t in tools}

        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
        )
        llm_with_tools = llm.bind_tools(tools)

    except Exception as e:
        # Return a stub executor so the endpoint never breaks
        err_msg = f"Initialization error: {type(e).__name__}: {e}"
        def _fail(_payload: Dict[str, Any]) -> Dict[str, str]:
            return {"output": err_msg}
        return _fail

    def _invoke(payload: Dict[str, Any]) -> Dict[str, str]:
        question: str = payload.get("input", "")
        history = payload.get("chat_history", [])

        msgs: List[BaseMessage] = [SystemMessage(content=SYSTEM)]

        # Accept either dicts or LC BaseMessage objects
        for m in history:
            if isinstance(m, BaseMessage):
                msgs.append(m)
                continue
            if isinstance(m, dict):
                role = (m.get("role") or m.get("type") or "").lower()
                content = m.get("content", "")
                if role in ("assistant", "ai"):
                    msgs.append(AIMessage(content=content))
                else:
                    msgs.append(HumanMessage(content=content))
            else:
                msgs.append(HumanMessage(content=str(m)))

        msgs.append(HumanMessage(content=question))

        # Up to 4 tool-calling rounds
        for _ in range(4):
            ai: AIMessage = llm_with_tools.invoke(msgs)
            
            msgs.append(ai)

            # Normalize tool_calls across versions
            raw_calls = getattr(ai, "tool_calls", None) or []
            tool_calls = []
            for idx, c in enumerate(raw_calls):
                if isinstance(c, dict):
                    tool_calls.append({
                        "id": c.get("id") or f"call_{idx}",
                        "name": c.get("name"),
                        "args": c.get("args", {}) or {},
                    })
                else:
                    tool_calls.append({
                        "id": getattr(c, "id", None) or f"call_{idx}",
                        "name": getattr(c, "name", None),
                        "args": getattr(c, "args", {}) or {},
                    })

            if not tool_calls:
                return {"output": ai.content}

            for call in tool_calls:
                tool_name = call["name"]
                args = call.get("args", {}) or {}
                tool = name_to_tool.get(tool_name)
                if not tool:
                    msgs.append(ToolMessage(
                        content=f"Tool '{tool_name}' is not available.",
                        tool_call_id=call["id"],
                    ))
                    continue
                try:
                    result = tool.invoke(args)
                except Exception as e:
                    result = {"error": f"{type(e).__name__}: {e}"}

                msgs.append(ToolMessage(
                    content=str(result),
                    tool_call_id=call["id"],
                ))

        return {"output": "I couldn’t confidently complete this with the available tools. Try rephrasing or narrowing the query."}

    return _invoke
