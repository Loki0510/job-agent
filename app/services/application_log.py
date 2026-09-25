from datetime import datetime, timezone

_entries=[]

def add(entry):
    item=dict(entry)
    item["reported_at"]=datetime.now(timezone.utc).isoformat()
    _entries.append(item)
    if len(_entries)>1000:
        del _entries[:-1000]
    return item

def entries():
    return list(reversed(_entries))
