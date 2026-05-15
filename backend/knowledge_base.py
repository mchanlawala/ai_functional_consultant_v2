"""knowledge_base.py — ChromaDB RAG KB from meeting transcripts."""
import json, os
from datetime import datetime

KB_DIR = os.path.join(os.path.dirname(__file__),"data","knowledge_bases")
os.makedirs(KB_DIR, exist_ok=True)
_registry = {}

class SessionKB:
    def __init__(self, session_id):
        self.session_id  = session_id
        self.persist_dir = os.path.join(KB_DIR, session_id)
        os.makedirs(self.persist_dir, exist_ok=True)
        self._meta_path  = os.path.join(self.persist_dir,"meta.json")
        self._meta       = self._load_meta()
        self._vs         = None

    def _load_meta(self):
        if os.path.exists(self._meta_path):
            try:
                with open(self._meta_path) as f: return json.load(f)
            except Exception: pass
        return {"meetings":[],"total_chunks":0,"created_at":datetime.utcnow().isoformat()}

    def _save_meta(self):
        with open(self._meta_path,"w") as f:
            json.dump(self._meta,f,indent=2,default=str)

    def _vs_(self):
        if self._vs is None:
            from langchain_chroma import Chroma   # ✅ fixed import
            from llm_factory import get_embeddings
            self._vs = Chroma(collection_name=f"fc_{self.session_id}",
                              embedding_function=get_embeddings(),
                              persist_directory=self.persist_dir)
        return self._vs

    def add_meeting(self, transcript, screen_descs, meeting_name, mom_text=""):
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        screen = "\n".join(screen_descs)
        combined = f"# Meeting: {meeting_name}\n## Transcript\n{transcript}\n\n## Screen\n{screen}\n"
        if mom_text: combined += f"\n## MoM\n{mom_text}\n"
        docs = RecursiveCharacterTextSplitter(chunk_size=800,chunk_overlap=100).create_documents(
            [combined],[{"meeting":meeting_name,"session":self.session_id,"type":"transcript",
                         "added_at":datetime.utcnow().isoformat()}])
        self._vs_().add_documents(docs)
        self._meta["meetings"].append({"name":meeting_name,"chunks":len(docs),
                                       "transcript_len":len(transcript),"added_at":datetime.utcnow().isoformat()})
        self._meta["total_chunks"] = self._meta.get("total_chunks",0)+len(docs)
        self._save_meta()
        self.save_raw_transcript(meeting_name, transcript)
        return len(docs)

    def add_text(self, text, source, doc_type="document"):
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        docs = RecursiveCharacterTextSplitter(chunk_size=800,chunk_overlap=100).create_documents(
            [text],[{"source":source,"type":doc_type,"session":self.session_id}])
        self._vs_().add_documents(docs)
        self._meta["total_chunks"] = self._meta.get("total_chunks",0)+len(docs)
        self._save_meta()
        return len(docs)

    def query(self, question, k=6):
        try:
            docs = self._vs_().similarity_search(question, k=k)
            return "\n\n---\n\n".join(d.page_content for d in docs)
        except Exception: return ""

    def get_full_context(self, max_chars=18000):
        try:
            docs = self._vs_().similarity_search("meeting transcript requirements process business",k=30)
            return "\n\n---\n\n".join(d.page_content for d in docs)[:max_chars]
        except Exception: return ""

    def get_info(self):
        return {"session_id":self.session_id,"meetings":self._meta.get("meetings",[]),
                "total_chunks":self._meta.get("total_chunks",0),"created_at":self._meta.get("created_at")}

    def save_raw_transcript(self, meeting_name, text):
        path = os.path.join(self.persist_dir,f"{meeting_name.replace(' ','_')}_raw.txt")
        with open(path,"w",encoding="utf-8") as f: f.write(text)

def get_kb(session_id):
    if session_id not in _registry:
        _registry[session_id] = SessionKB(session_id)
    return _registry[session_id]