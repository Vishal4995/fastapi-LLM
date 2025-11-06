# app/orchestrator.py
from __future__ import annotations
from typing import List, Dict, Callable, Any
import json
import re
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_openai import ChatOpenAI

from .classifier import classify_query
from .tools import build_tools
from .rg_templates import build_system_prompt

ALL_RX = re.compile(r"\b(all|entire|complete|every)\b.*\bemploye?es?\b", re.I)
LIST_RX = re.compile(r"\b(list|show|employee list|all employees)\b", re.I)
COUNT_RX = re.compile(r"\b(how many|count|total employees?)\b", re.I)

def _json(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(obj)

def make_fast_executor(db) -> Callable[[Dict[str, Any]], Dict[str, str]]:
    """
    Domain-aware, tool-pruned executor with fast-paths for common employee queries.
    """
    try:
        all_tools = build_tools(db)
        tool_map = {t.name: t for t in all_tools}

        domain_tool_names = {
            "employee":   ["search_employees", "get_employee", "get_employee_count", "attendance_summary"],
            "attendance": ["attendance_on", "attendance_summary", "search_employees", "get_employee"],
            "department": ["list_departments", "search_employees"],
            "project":    ["list_projects", "search_employees"],
            "unknown":    ["search_employees", "list_departments", "list_projects"],
        }

        def _exec(payload: Dict[str, Any]) -> Dict[str, str]:
            q = payload.get("input", "")
            history = payload.get("chat_history", [])

            domain = classify_query(q)
            names = domain_tool_names.get(domain, domain_tool_names["unknown"])
            tools = [tool_map[n] for n in names if n in tool_map]
            name_to_tool = {t.name: t for t in tools}

            # ---------- FAST PATHS ----------
            if domain == "employee":
                if COUNT_RX.search(q):
                    res = name_to_tool["get_employee_count"].invoke({})
                    total = (res or {}).get("total_employees", 0)
                    return {"output": f"There are {total} employees."}
                if ALL_RX.search(q):
                    res = name_to_tool["search_employees"].invoke({"limit": -1})
                    if isinstance(res, list) and res:
                        lines = []
                        for r in res:
                            if "info" in r:
                                lines.append(f"- {r['info']}")
                            else:
                                nm = f"{r.get('first_name','')} {r.get('last_name','')}".strip()
                                ti = r.get("title") or "-"
                                dp = r.get("department") or "-"
                                pj = r.get("project") or "-"
                                dj = r.get("date_joined") or "-"
                                lines.append(f"- {nm} — {ti} — {dp} — {pj} — {dj}")
                        return {"output": "All employees:\n" + "\n".join(lines)}
                    else:
                        return {"output": "No employees found."}
                if LIST_RX.search(q):
                    res = name_to_tool["search_employees"].invoke({"limit": 10})
                    if isinstance(res, list) and res:
                        lines = []
                        for r in res[:10]:
                            # handle both normal rows and 'info' fallback
                            if "info" in r:
                                lines.append(f"- {r['info']}")
                            else:
                                nm = f"{r.get('first_name','')} {r.get('last_name','')}".strip()
                                ti = r.get("title") or "-"
                                dp = r.get("department") or "-"
                                pj = r.get("project") or "-"
                                dj = r.get("date_joined") or "-"
                                lines.append(f"- {nm} — {ti} — {dp} — {pj} — {dj}")
                        return {"output": "Showing up to 10 employees:\n" + "\n".join(lines)}
                    else:
                        # If truly empty, still return a friendly message
                        return {"output": "No employees found."}
            # --------------------------------

            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            llm_with_tools = llm.bind_tools(tools)

            sys = SystemMessage(content=build_system_prompt(domain))
            msgs: List[BaseMessage] = [sys]

            for m in history:
                if isinstance(m, BaseMessage):
                    msgs.append(m)
                elif isinstance(m, dict):
                    role = (m.get("role") or m.get("type") or "user").lower()
                    content = m.get("content", "")
                    if role in ("assistant", "ai"):
                        msgs.append(AIMessage(content=content))
                    else:
                        msgs.append(HumanMessage(content=content))
                else:
                    msgs.append(HumanMessage(content=str(m)))

            msgs.append(HumanMessage(content=q))

            # up to 6 tool rounds
            for _ in range(6):
                ai: AIMessage = llm_with_tools.invoke(msgs)
                msgs.append(ai)

                raw_calls = getattr(ai, "tool_calls", None) or []
                calls = []
                for i, c in enumerate(raw_calls):
                    if isinstance(c, dict):
                        calls.append({
                            "id": c.get("id") or f"call_{i}",
                            "name": c.get("name"),
                            "args": c.get("args") or {},
                        })
                    else:
                        calls.append({
                            "id": getattr(c, "id", None) or f"call_{i}",
                            "name": getattr(c, "name", None),
                            "args": getattr(c, "args", {}) or {},
                        })

                if not calls:
                    return {"output": ai.content, "domain": domain}

                for call in calls:
                    tool = name_to_tool.get(call["name"])
                    if not tool:
                        msgs.append(ToolMessage(
                            content=_json({"error": f"Tool '{call['name']}' not available for domain '{domain}'"}),
                            tool_call_id=call["id"],
                        ))
                        continue
                    try:
                        res = tool.invoke(call["args"])
                    except Exception as e:
                        res = {"error": f"{type(e).__name__}: {e}"}

                    # send JSON back to the model
                    msgs.append(ToolMessage(content=_json(res), tool_call_id=call["id"]))

            return {"output": "Couldn’t complete with available tools. Try narrowing the query.", "domain": domain}

        return _exec
    except Exception as e:
        err = f"Init error: {type(e).__name__}: {e}"
        def _fail(_): return {"output": err, "domain": "unknown"}
        return _fail
