# app/utils.py
import json
from sqlalchemy.orm import Session
from sqlalchemy import text

def run_sql(db: Session, sql: str) -> list[dict]:
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

def to_json_str(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
