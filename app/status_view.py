from app.worker_state import read_history

def latest_categorized():
    latest={}
    for item in read_history(10000):
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
