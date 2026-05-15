import json, re
def parse_json(text, fallback=None):
    if not text: return fallback if fallback is not None else {}
    cleaned = text
    for pat in (r"```json\s*\n?(.*?)```", r"```\s*\n?(.*?)```"):
        m = re.search(pat, cleaned, re.DOTALL)
        if m: cleaned = m.group(1).strip(); break
    try: return json.loads(cleaned)
    except Exception: pass
    for pat in (r"\{.*\}", r"\[.*\]"):
        m = re.search(pat, cleaned, re.DOTALL)
        if m:
            try: return json.loads(m.group(0))
            except Exception: pass
    return fallback if fallback is not None else {}
