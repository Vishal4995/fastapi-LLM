# app/routers/qa.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from ..database import get_db

# Legacy agent (generic) – keep if you want:
from ..agent import make_executor

# Fast orchestrator (domain-aware)
from ..orchestrator import make_fast_executor

router = APIRouter(prefix="/qa", tags=["qa"])


class AskAgentReq(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    history: List[Dict[str, Any]] = Field(default_factory=list)

class AskAgentResp(BaseModel):
    answer: str


@router.post("/ask-agent", response_model=AskAgentResp)
def ask_agent(req: AskAgentReq, db: Session = Depends(get_db)):
    executor = make_executor(db)   # generic agent (your existing agent.py)
    result = executor({"input": req.question, "chat_history": req.history})
    return AskAgentResp(answer=result.get("output", ""))


@router.post("/ask-fast", response_model=AskAgentResp)
def ask_fast(req: AskAgentReq, db: Session = Depends(get_db)):
    executor = make_fast_executor(db)  # domain-aware orchestrator
    result = executor({"input": req.question, "chat_history": req.history})
    return AskAgentResp(answer=result.get("output", ""))
