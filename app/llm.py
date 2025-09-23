# app/llm.py
import os
from typing import Literal
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# You may pick a model suitable for reasoning + tool use.
# Keep it configurable via env if you like.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # or gpt-5 if available

def generate_sql(system_prompt: str, user_question: str) -> str:
    """
    Use Chat Completions API to get a single SQL string.
    """
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ],
        temperature=0.0,
    )
    sql = resp.choices[0].message.content.strip()
    return sql

def explain_answer(user_question: str, sql: str, rows_json: str) -> str:
    """
    Ask the model to verbalize the result set.
    """
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Follow the instructions strictly."},
            {"role": "user", "content": f"{ANSWER_INSTRUCTION(user_question, sql, rows_json)}"},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

def ANSWER_INSTRUCTION(q: str, sql: str, rows: str) -> str:
    return (
        "Instruction:\n"
        + "You will turn the SQL results into a concise, human-readable answer.\n\n"
        + f"Question:\n{q}\n\n"
        + f"SQL:\n{sql}\n\n"
        + f"Rows (JSON):\n{rows}\n"
    )
