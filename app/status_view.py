import json
import os
from app.worker_state import read_history

def _email_confirmed_ids():
    raw=os.getenv("EMAIL_CONFIRMED_IDS_JSON","[]")
    try:
        value=json.loads(raw)
        return set(str(x) for x in value) if isinstance(value,list) else set()
    except Exception:
        return set()

def latest_categorized():
    confirmed=_email_confirmed_ids()
    latest={}
    for item in read_history(10000):
        external_id=item.get("external_id")
        if external_id and external_id not in latest:
            latest[external_id]=dict(item)

    groups={"applied":[],"manual_required":[],"blocked":[],"ready":[],"unconfirmed":[]}
    for item in latest.values():
        external_id=item.get("external_id")
        if external_id in confirmed:
            item["status"]="submitted"
            item["mode"]="email_confirmed"
            item["reason"]="application confirmed by Gmail"
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
