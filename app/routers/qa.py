# app/routers/qa.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..database import get_db
from ..prompts import SCHEMA_GUIDE, ANSWER_GUIDE
from ..llm import generate_sql, explain_answer
from ..sqlguard import is_safe_select, ensure_limit
from ..utils import run_sql, to_json_str

router = APIRouter(prefix="/qa", tags=["qa"])

class AskReq(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)

class AskResp(BaseModel):
    sql: str
    rows: list[dict]
    answer: str

@router.post("/ask", response_model=AskResp)
def ask(req: AskReq, db: Session = Depends(get_db)):
    # 1) LLM -> SQL
    sql_raw = generate_sql(SCHEMA_GUIDE, req.question)

    # 2) Guardrails
    if not is_safe_select(sql_raw):
        raise HTTPException(status_code=400, detail="Unsafe or invalid SQL produced.")
    sql = ensure_limit(sql_raw)

    # 3) Execute
    try:
        rows = run_sql(db, sql)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {e}")

    # 4) LLM -> natural answer
    answer = explain_answer(req.question, sql, to_json_str(rows))

    return AskResp(sql=sql, rows=rows, answer=answer)
