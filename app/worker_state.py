import json
import os
import pathlib
from datetime import datetime, timezone

DATA_DIR=pathlib.Path(os.getenv("WORKER_DATA_DIR","/data"))
HISTORY_PATH=DATA_DIR/"application_history.jsonl"
BASELINE_PATH=DATA_DIR/"auto_submit_baseline.json"

def _now():
    return datetime.now(timezone.utc).isoformat()

def append_history(entry):
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    item=dict(entry)
    item.setdefault("recorded_at",_now())
    with HISTORY_PATH.open("a",encoding="utf-8") as handle:
        handle.write(json.dumps(item,ensure_ascii=False)+"\n")
    return item

def read_history(limit=1000):
    if not HISTORY_PATH.exists():
        return []
    rows=[]
    with HISTORY_PATH.open("r",encoding="utf-8") as handle:
        for line in handle:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return list(reversed(rows[-limit:]))

def terminal_ids():
    result=set()
    for item in read_history(10000):
        if item.get("status") in {"submitted","manual_required","submit_unconfirmed"}:
            external_id=item.get("external_id")
            if external_id:
                result.add(external_id)
    return result

def has_baseline():
    return BASELINE_PATH.exists()

def save_baseline(ids):
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    payload={"created_at":_now(),"external_ids":sorted(set(ids))}
    BASELINE_PATH.write_text(json.dumps(payload,indent=2),encoding="utf-8")
    return payload

def baseline_ids():
    if not BASELINE_PATH.exists():
        return set()
    try:
        payload=json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        return set(payload.get("external_ids") or [])
    except Exception:
        return set()

def categorized():
    latest={}
    for item in reversed(read_history(10000)):
        external_id=item.get("external_id")
        if external_id and external_id not in latest:
            latest[external_id]=item

    groups={"applied":[],"manual_required":[],"blocked":[],"ready":[],"unconfirmed":[]}
    for item in latest.values():
        status=item.get("status")
        if status=="submitted":
            groups["applied"].append(item)
        elif status=="manual_required" or (status=="ready" and item.get("captcha_detected")):
            groups["manual_required"].append(item)
        elif status=="ready":
            groups["ready"].append(item)
        elif status=="submit_unconfirmed":
            groups["unconfirmed"].append(item)
        else:
            groups["blocked"].append(item)
    return groups
