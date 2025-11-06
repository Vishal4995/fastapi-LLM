# app/classifier.py
from __future__ import annotations
from typing import Literal, Tuple, Dict, List
import re
import os
from functools import lru_cache

Domain = Literal["employee", "attendance", "department", "project", "unknown"]

# Fast keyword rules (zero-latency, works offline)
KEYS: Dict[Domain, List[str]] = {
    "employee":   ["employee", "employees", "title", "joined", "join date", "email", "manager", "hire", "reportee"],
    "attendance": ["attendance", "present", "absent", "wfh", "leave", "late", "timesheet"],
    "department": ["department", "dept", "org unit", "headcount"],
    "project":    ["project", "client", "assignment", "staffing"],
}

PATTERNS: Dict[Domain, List[re.Pattern]] = {
    d: [re.compile(rf"\b{re.escape(k)}\b", re.I) for k in ks] for d, ks in KEYS.items()
}

def _keyword_vote(q: str) -> Tuple[Domain, int]:
    votes = {d: 0 for d in KEYS}
    for d, regs in PATTERNS.items():
        for r in regs:
            if r.search(q):
                votes[d] += 1
    best = max(votes.items(), key=lambda x: x[1])
    return (best[0], best[1])

# Optional embedding fallback for ambiguous queries
_EMBED = None
_DOM_TEXT = {
    "employee":   "employees: names, emails, titles, date joined, department, project",
    "attendance": "attendance: present/absent/wfh/leave by date, summaries by period",
    "department": "departments: department names, descriptions, headcount",
    "project":    "projects: project names, client, staffing",
}

def _lazy_init_embed():
    global _EMBED
    if _EMBED is None:
        try:
            from langchain_openai import OpenAIEmbeddings
            _EMBED = OpenAIEmbeddings(model=os.getenv("EMBED_MODEL", "text-embedding-3-small"))
        except Exception:
            _EMBED = False
    return _EMBED

@lru_cache(maxsize=64)
def _embed(t: str):
    E = _lazy_init_embed()
    if not E:
        return None
    return E.embed_query(t)

def _cos(a: List[float], b: List[float]) -> float:
    import math
    if not a or not b:
        return 0.0
    da = math.sqrt(sum(x*x for x in a))
    db = math.sqrt(sum(x*x for x in b))
    if da == 0 or db == 0:
        return 0.0
    return sum(x*y for x, y in zip(a, b)) / (da * db)

def classify_query(question: str) -> Domain:
    q = (question or "").strip()
    if not q:
        return "unknown"

    dom, votes = _keyword_vote(q)
    if votes >= 2:
        return dom

    # ambiguous → embeddings if available
    qe = _embed(q)
    if qe:
        best_dom, best_sim = "unknown", 0.0
        for d, txt in _DOM_TEXT.items():
            de = _embed(txt)
            if de:
                sim = _cos(qe, de)
                if sim > best_sim:
                    best_dom, best_sim = d, sim
        if best_sim > 0.65:
            return best_dom

    return dom if votes >= 1 else "unknown"
