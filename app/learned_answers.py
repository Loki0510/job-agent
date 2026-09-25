import json
import os
import pathlib
import re
from datetime import datetime, timezone

DATA_DIR=pathlib.Path(os.getenv("WORKER_DATA_DIR","/data"))
ANSWERS_PATH=DATA_DIR/"learned_answers.json"

def normalize(value):
    return re.sub(r"[^a-z0-9]+"," ",(value or "").lower()).strip()

def _load():
    if not ANSWERS_PATH.exists():
        return {}
    try:
        value=json.loads(ANSWERS_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value,dict) else {}
    except Exception:
        return {}

def _save(data):
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    ANSWERS_PATH.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")

def key(question,company=""):
    return f"{normalize(company)}::{normalize(question)}"

def get_answer(question,company=""):
    data=_load()
    exact=data.get(key(question,company))
    if exact is not None:
        return exact.get("answer")
    generic=data.get(key(question,""))
    return generic.get("answer") if generic is not None else None

def set_answer(question,answer,company="",scope="company"):
    data=_load()
    target_company=company if scope=="company" else ""
    k=key(question,target_company)
    data[k]={
        "question":question,
        "company":target_company,
        "answer":answer,
        "updated_at":datetime.now(timezone.utc).isoformat(),
    }
    _save(data)
    return data[k]

def all_answers():
    return list(_load().values())
