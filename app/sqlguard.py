# app/sqlguard.py
import re

READONLY_PATTERN = re.compile(r"^\s*select\b", re.IGNORECASE | re.DOTALL)
FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate)\b", re.IGNORECASE)
WHITELISTED_TABLES = {"employees", "departments", "projects", "attendance"}

def is_safe_select(sql: str) -> bool:
    if not READONLY_PATTERN.match(sql):
        return False
    if FORBIDDEN.search(sql):
        return False
    # crude whitelist enforcement
    tables = re.findall(r"\bfrom\s+([a-z_][a-z0-9_]*)(?:\s|$)", sql, flags=re.IGNORECASE)
    joins = re.findall(r"\bjoin\s+([a-z_][a-z0-9_]*)", sql, flags=re.IGNORECASE)
    for t in (tables + joins):
        if t.lower() not in WHITELISTED_TABLES:
            return False
    return True

def ensure_limit(sql: str, default_limit=50) -> str:
    if re.search(r"\blimit\s+\d+", sql, flags=re.IGNORECASE):
        return sql
    # don't force limit for aggregate-only queries that return a single row
    if re.search(r"\bcount\s*\(", sql, flags=re.IGNORECASE) and "group by" not in sql.lower():
        return sql
    return sql.rstrip().rstrip(";") + f" LIMIT {default_limit};"
