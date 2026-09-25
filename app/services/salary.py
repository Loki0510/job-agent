def annualize_salary(value, interval):
    if value is None: return None
    interval=(interval or "").lower()
    mult={"year":1,"annual":1,"month":12,"week":52,"day":260,"hour":2080}.get(interval,1)
    try: return int(float(value)*mult)
    except Exception: return None
