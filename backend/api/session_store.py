"""api/session_store.py — Thread-safe session state store."""
import json,os,threading
from datetime import datetime
SESSIONS_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)),"data","sessions")
os.makedirs(SESSIONS_DIR,exist_ok=True)

class SessionStore:
    def __init__(self):
        self._s={}; self._lock=threading.RLock()

    def create(self,sid,project_name="Project"):
        now=datetime.utcnow().isoformat()
        s={"session_id":sid,"project_name":project_name,"status":"idle",
           "meetings":[],"kb_chunks":0,"documents":[],"progress":0,
           "current_step":"Ready","error":None,"review_comments":None,
           "created_at":now,"updated_at":now,"zip_path":None}
        with self._lock: self._s[sid]=s; self._save(sid)
        return s

    def get(self,sid):
        with self._lock:
            if sid not in self._s:
                d=self._load(sid)
                if d: self._s[sid]=d
            return self._s.get(sid)

    def update(self,sid,**kw):
        with self._lock:
            if sid not in self._s: return None
            self._s[sid].update(kw)
            self._s[sid]["updated_at"]=datetime.utcnow().isoformat()
            self._save(sid); return self._s[sid]

    def list_all(self):
        with self._lock:
            try:
                for f in os.listdir(SESSIONS_DIR):
                    if f.endswith(".json"):
                        sid=f[:-5]
                        if sid not in self._s:
                            d=self._load(sid)
                            if d: self._s[sid]=d
            except Exception: pass
            return list(self._s.values())

    def _save(self,sid):
        try:
            with open(os.path.join(SESSIONS_DIR,f"{sid}.json"),"w") as f:
                json.dump(self._s[sid],f,indent=2,default=str)
        except Exception: pass

    def _load(self,sid):
        try:
            p=os.path.join(SESSIONS_DIR,f"{sid}.json")
            if os.path.exists(p):
                with open(p) as f: return json.load(f)
        except Exception: pass
        return None

store=SessionStore()
