"""api/routes.py — All REST + WebSocket endpoints."""
import os,sys,uuid,shutil
from fastapi import APIRouter,BackgroundTasks,File,Form,HTTPException,UploadFile,WebSocket,WebSocketDisconnect
from fastapi.responses import FileResponse,HTMLResponse
from pydantic import BaseModel
from typing import Optional
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from api.session_store import store
from api.workflow import register_ws,unregister_ws,start_video_processing,start_document_generation

UPLOADS_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)),"data","uploads")
OUTPUTS_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)),"data","outputs")
os.makedirs(UPLOADS_DIR,exist_ok=True); os.makedirs(OUTPUTS_DIR,exist_ok=True)
router=APIRouter()

class CreateSession(BaseModel):
    project_name:str="Project"

class ReviewDecision(BaseModel):
    session_id:str; decision:str
    comments:Optional[str]=None; document_feedback:Optional[dict]=None

@router.post("/sessions/create")
async def create_session(req:CreateSession):
    sid=str(uuid.uuid4())[:8]; store.create(sid,req.project_name)
    return {"session_id":sid,"status":"idle","message":f"Session '{req.project_name}' created."}

@router.get("/sessions")
async def list_sessions(): return store.list_all()

@router.get("/sessions/{sid}")
async def get_session(sid:str):
    s=store.get(sid)
    if not s: raise HTTPException(404,"Session not found")
    return s

@router.delete("/sessions/{sid}")
async def delete_session(sid:str):
    s=store.get(sid)
    if not s: raise HTTPException(404,"Session not found")
    out=os.path.join(OUTPUTS_DIR,sid)
    if os.path.exists(out): shutil.rmtree(out,ignore_errors=True)
    return {"message":f"Session {sid} deleted"}

@router.post("/sessions/{sid}/upload")
async def upload_video(sid:str,bg:BackgroundTasks,
                       file:UploadFile=File(...),meeting_name:str=Form(default="")):
    s=store.get(sid)
    if not s: raise HTTPException(404,"Session not found")
    if s["status"]=="processing": raise HTTPException(400,"Already processing a video. Wait for it to finish.")
    if not file.filename.lower().endswith((".mp4",".avi",".mov",".mkv",".webm")):
        raise HTTPException(400,"Only video files accepted: mp4, avi, mov, mkv, webm")
    upload_dir=os.path.join(UPLOADS_DIR,sid); os.makedirs(upload_dir,exist_ok=True)
    safe=file.filename.replace(" ","_"); video_path=os.path.join(upload_dir,safe)
    content=await file.read()
    with open(video_path,"wb") as f: f.write(content)
    name=meeting_name.strip() or os.path.splitext(file.filename)[0]
    store.update(sid,status="processing",progress=0,current_step=f"Queued: {name}")
    bg.add_task(start_video_processing,sid,video_path,name)
    return {"message":f"Upload received. Processing '{name}'...","session_id":sid,
            "meeting_name":name,"file_size_mb":round(len(content)/1024/1024,2)}

@router.post("/sessions/{sid}/generate")
async def generate_documents(sid:str,bg:BackgroundTasks):
    s=store.get(sid)
    if not s: raise HTTPException(404,"Session not found")
    if not s.get("meetings"): raise HTTPException(400,"No meetings processed yet. Upload MP4 files first.")
    if s["status"]=="processing": raise HTTPException(400,"Video still processing.")
    if s["status"]=="generating": raise HTTPException(400,"Already generating documents.")
    store.update(sid,status="generating",progress=0,current_step="Starting...")
    bg.add_task(start_document_generation,sid)
    return {"session_id":sid,"status":"generating",
            "message":f"Generating 7 consulting documents from {len(s['meetings'])} meetings..."}

@router.post("/sessions/{sid}/review")
async def review(sid:str,req:ReviewDecision):
    s=store.get(sid)
    if not s: raise HTTPException(404,"Session not found")
    if req.decision=="approve":
        docs=s.get("documents",[])
        for d in docs:
            d["approved"]=True
            if req.document_feedback and d["id"] in req.document_feedback:
                d["feedback"]=req.document_feedback[d["id"]]
        store.update(sid,status="approved",documents=docs,review_comments=req.comments,
                     progress=99,current_step="Approved — ready to publish")
        return {"message":"All documents approved.","status":"approved"}
    elif req.decision=="request_changes":
        store.update(sid,review_comments=req.comments,current_step="Changes requested")
        return {"message":"Changes requested.","status":s["status"]}
    elif req.decision=="reject":
        store.update(sid,status="idle",review_comments=req.comments,progress=0,
                     current_step="Rejected — upload new recordings")
        return {"message":"Rejected.","status":"idle"}
    raise HTTPException(400,f"Unknown decision: {req.decision}")

@router.post("/sessions/{sid}/approve-document")
async def approve_doc(sid:str,doc_id:str,feedback:str=""):
    s=store.get(sid)
    if not s: raise HTTPException(404,"Session not found")
    docs=s.get("documents",[])
    for d in docs:
        if d["id"]==doc_id: d["approved"]=True; d["feedback"]=feedback
    store.update(sid,documents=docs)
    return {"message":f"Document {doc_id} approved"}

@router.post("/sessions/{sid}/publish")
async def publish(sid:str):
    s=store.get(sid)
    if not s: raise HTTPException(404,"Session not found")
    if s["status"] not in ("approved","reviewing"): raise HTTPException(400,"Must be approved first")
    store.update(sid,status="published",progress=100,current_step="Published")
    return {"message":"Package published","status":"published",
            "download_url":f"/api/sessions/{sid}/download"}

@router.get("/sessions/{sid}/download")
async def download_package(sid:str):
    s=store.get(sid)
    if not s: raise HTTPException(404,"Session not found")
    zp=s.get("zip_path") or os.path.join(OUTPUTS_DIR,sid,"consulting_package.zip")
    if not os.path.exists(zp): raise HTTPException(404,"Package not ready yet")
    return FileResponse(zp,media_type="application/zip",filename=f"consulting_package_{sid}.zip")

@router.get("/sessions/{sid}/document/{doc_id}")
async def download_doc(sid:str,doc_id:str):
    s=store.get(sid)
    if not s: raise HTTPException(404,"Session not found")
    doc=next((d for d in s.get("documents",[]) if d["id"]==doc_id),None)
    if not doc or not doc.get("file_path"): raise HTTPException(404,"Document not found")
    fp=doc["file_path"]
    if not os.path.exists(fp): raise HTTPException(404,"File missing")
    ext=os.path.splitext(fp)[1].lower()
    mt=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if ext==".docx" else "text/markdown" if ext==".md" else "application/octet-stream")
    return FileResponse(fp,media_type=mt,filename=os.path.basename(fp))

@router.get("/sessions/{sid}/preview/{doc_id}")
async def preview_doc(sid:str,doc_id:str):
    s=store.get(sid)
    if not s: raise HTTPException(404,"Session not found")
    doc=next((d for d in s.get("documents",[]) if d["id"]==doc_id),None)
    if not doc or not doc.get("file_path"): raise HTTPException(404,"Document not found")
    fp=doc["file_path"]
    if not os.path.exists(fp): raise HTTPException(404,"File missing")
    ext=os.path.splitext(fp)[1].lower()
    if ext==".docx":
        try:
            from docx import Document as DocxDoc
            d=DocxDoc(fp); paras=[p.text for p in d.paragraphs if p.text.strip()]
            html_content="<br/>".join(f"<p>{t}</p>" for t in paras)
        except Exception as e: html_content=f"<p>Preview error: {e}</p>"
        return HTMLResponse(f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>{doc['name']}</title>
<style>body{{font-family:-apple-system,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;line-height:1.7;color:#1e293b;}}
h2{{color:#0F1F38;border-bottom:2px solid #e2e8f0;padding-bottom:8px;}}
p{{margin-bottom:8px;font-size:14px;}}
</style></head><body>
<h2>{doc['name']}</h2>
<div style='background:#f8fafc;padding:16px;border-radius:8px;font-size:12px;color:#64748b;margin-bottom:16px;'>
Word document preview — download for full formatting</div>
{html_content}</body></html>""")
    if ext==".md":
        with open(fp,encoding="utf-8") as f: md=f.read()
        import markdown as mdlib
        html=mdlib.markdown(md,extensions=["tables","fenced_code"])
        return HTMLResponse(f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>{doc['name']}</title>
<style>body{{font-family:-apple-system,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;line-height:1.7;color:#1e293b;}}
table{{border-collapse:collapse;width:100%;margin:16px 0;}}
th{{background:#0F1F38;color:white;padding:10px 14px;text-align:left;font-size:13px;}}
td{{padding:9px 14px;border-top:1px solid #e2e8f0;font-size:13px;}}
tr:nth-child(even)td{{background:#f8fafc;}}
h1,h2,h3{{color:#0F1F38;}}h2{{border-bottom:2px solid #e2e8f0;padding-bottom:8px;}}
code{{background:#f1f5f9;padding:2px 6px;border-radius:4px;}}
pre{{background:#1e293b;color:#93c5fd;padding:16px;border-radius:8px;overflow-x:auto;}}
</style></head><body>{html}</body></html>""")
    return FileResponse(fp,headers={"Content-Disposition":"inline"})

@router.get("/status")
async def server_status():
    from video_processor import check_ollama,get_ollama_models
    ok=check_ollama(); models=get_ollama_models() if ok else []
    tm=os.getenv("TEXT_MODEL","llama3.2:latest"); lm=os.getenv("LLM_MODEL","qwen2.5:14b")
    vm=os.getenv("VISION_MODEL","llava:latest")
    return {"ollama_connected":ok,"available_models":models,
            "text_model":tm,"text_model_ok":any(tm in m for m in models),
            "llm_model":lm,"llm_model_ok":any(lm in m for m in models),
            "vision_model":vm,"vision_model_ok":any(vm in m for m in models)}

@router.websocket("/ws/{sid}")
async def ws_endpoint(ws:WebSocket,sid:str):
    await ws.accept(); register_ws(sid,ws)
    s=store.get(sid)
    if s: await ws.send_json({"type":"state","session_id":sid,"data":s})
    try:
        while True:
            msg=await ws.receive_text()
            if msg=="ping": await ws.send_text("pong")
    except WebSocketDisconnect: unregister_ws(sid,ws)
