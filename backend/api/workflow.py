"""api/workflow.py — Background workflow threads with WebSocket progress."""
import asyncio, builtins, json, os, sys, threading, traceback, zipfile
import concurrent.futures
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from api.session_store import store

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

_ws = {}
_lock = threading.Lock()

def register_ws(sid, ws):
    with _lock:
        _ws.setdefault(sid, set()).add(ws)

def unregister_ws(sid, ws):
    with _lock:
        _ws.get(sid, set()).discard(ws)

async def _broadcast(sid, msg):
    with _lock:
        conns = list(_ws.get(sid, set()))
    for ws in conns:
        try:
            await ws.send_json(msg)
        except Exception:
            pass

def _emit(sid, progress, step, status=None, message="", data=None):
    upd = {"progress": progress, "current_step": step}
    if status:
        upd["status"] = status
    store.update(sid, **upd)
    payload = {
        "type": "progress",
        "session_id": sid,
        "progress": progress,
        "step": step,
        "message": message,
        "data": data or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_broadcast(sid, payload))
        loop.close()
    except Exception:
        pass

def process_single_video(sid, video_path, meeting_name):
    try:
        store.update(sid, status="processing")
        _emit(sid, 5, f"Processing: {meeting_name}", "processing", f"Starting pipeline for {meeting_name}...")
        from video_processor import process_video
        from agents.mom_agent import generate_mom_word
        from knowledge_base import get_kb
        session = store.get(sid)
        project_name = session.get("project_name", "Project")

        def prog(pct, msg):
            _emit(sid, 5 + int(pct * 0.55), f"{meeting_name}: {msg}", message=msg)

        result = process_video(video_path, progress_cb=prog, use_vision=True)
        transcript = result["transcript"]
        screen_descs = result["screen_descriptions"]
        _emit(sid, 62, f"{meeting_name}: Generating MoM", message="Generating Minutes of Meeting...")

        out_dir = os.path.join(OUTPUTS_DIR, sid)
        os.makedirs(out_dir, exist_ok=True)
        safe = meeting_name.replace(" ", "_").replace("/", "-")
        mom_path = os.path.join(out_dir, f"MoM_{safe}.docx")
        mom_text = generate_mom_word(transcript, screen_descs, meeting_name, project_name, mom_path)

        _emit(sid, 75, f"{meeting_name}: Building knowledge base", message="Adding to knowledge base...")
        kb = get_kb(sid)
        chunks = kb.add_meeting(transcript, screen_descs, meeting_name, mom_text)

        meetings = session.get("meetings", [])
        meetings.append({
            "name": meeting_name,
            "transcript_len": len(transcript),
            "frame_count": result["frame_count"],
            "chunks": chunks,
            "mom_path": mom_path,
            "mom_filename": f"MoM_{safe}.docx"
        })

        docs = session.get("documents", [])
        docs.append({
            "id": f"mom_{safe}",
            "num": str(len(docs) + 1).zfill(2),
            "name": f"MoM — {meeting_name}",
            "type": "mom",
            "description": f"Minutes of Meeting for {meeting_name}",
            "file_path": mom_path,
            "status": "generated",
            "approved": False,
            "feedback": None
        })

        store.update(sid,
                     meetings=meetings,
                     documents=docs,
                     kb_chunks=kb.get_info()["total_chunks"],
                     status="idle",
                     progress=100,
                     current_step=f"Processed: {meeting_name}")
        _emit(sid, 100, f"Done: {meeting_name}", "idle",
              f"MoM generated. {chunks} KB chunks added.",
              data={"meeting_name": meeting_name, "chunks": chunks, "transcript_len": len(transcript)})
        try:
            os.remove(video_path)
        except Exception:
            pass
    except Exception as e:
        store.update(sid, status="error", error=f"{meeting_name}: {e}\n{traceback.format_exc()}")
        _emit(sid, 0, "Error", "error", f"Failed: {meeting_name}: {e}")

# Helper function for parallel document generation
def _generate_single_document(gen_fn, kb, project_name, fpath, doc_id, doc_name, existing_moms, idx, sid):
    """Run one document generation and return the doc dict."""
    try:
        print(f"[DEBUG] Starting {doc_name} generation (parallel)...")
        gen_fn(kb, project_name, fpath)
        print(f"[DEBUG] {doc_name} generation completed.")
        # Add a snippet to knowledge base (optional)
        try:
            with open(fpath, "rb") as f:
                content = f.read().decode("utf-8", "ignore")[:3000]
                kb.add_text(content, doc_name, "generated")
        except Exception as e:
            print(f"[WARN] Could not add {doc_name} content to KB: {e}")
        return {
            "id": doc_id,
            "num": str(len(existing_moms) + idx + 1).zfill(2),
            "name": doc_name,
            "type": "consulting_doc",
            "description": f"AI-generated {doc_name}",
            "file_path": fpath,
            "status": "generated",
            "approved": False,
            "feedback": None
        }
    except Exception as e:
        print(f"[ERROR] Failed to generate {doc_name}: {e}")
        traceback.print_exc()
        return {
            "id": doc_id,
            "num": str(len(existing_moms) + idx + 1).zfill(2),
            "name": doc_name,
            "type": "consulting_doc",
            "description": f"Failed: {e}",
            "file_path": None,
            "status": "failed",
            "approved": False,
            "feedback": None
        }

def run_document_generation(sid):
    try:
        store.update(sid, status="generating")
        _emit(sid, 3, "Starting document generation", "generating", "Generating all consulting documents...")
        print(f"[DEBUG] Starting document generation for session {sid}")

        from knowledge_base import get_kb
        from agents.brd_agent import generate_brd_word
        from agents.frd_agent import generate_frd_word
        from agents.gap_analysis_agent import generate_gap_analysis_word
        from agents.process_flow_agent import generate_process_flow_word
        from agents.best_practices_agent import generate_best_practices_word
        from agents.requirement_spec_agent import generate_requirement_spec_word
        from agents.process_mining_agent import generate_process_mining_word
        from crews.functional_crew import FunctionalCrew

        session = store.get(sid)
        project_name = session.get("project_name", "Project")
        kb = get_kb(sid)
        out_dir = os.path.join(OUTPUTS_DIR, sid)
        os.makedirs(out_dir, exist_ok=True)

        # Skip CrewAI enrichment (domain analysis)
        #_emit(sid, 8, "Skipping domain analysis", message="Domain enrichment disabled")
        #print("⚠️ Skipping CrewAI domain enrichment")

        _emit(sid,8,"Running domain analysis",message="CrewAI domain knowledge enrichment...")
        try:
            context=kb.get_full_context(8000)
            reqs=session.get("requirements") or {}
            industry=reqs.get("industry","Manufacturing") if reqs else "Manufacturing"
            crew=FunctionalCrew(session["customer_query"] if session.get("customer_query") else "")
            enrichment=crew.run_domain_enrichment(industry,context)
            if enrichment.get("domain_knowledge"):
                kb.add_text(enrichment["domain_knowledge"],"domain_enrichment","enrichment")
        except Exception as de:
            print(f"Domain enrichment warning: {de}")

        existing_moms = [d for d in session.get("documents", []) if d.get("type") == "mom"]
        tasks = [
            ("brd", "Business Requirements Document BRD", "BRD.docx", generate_brd_word),
            ("frd", "Functional Requirements Document FRD", "FRD.docx", generate_frd_word),
            ("gap", "Gap Analysis Report", "Gap_Analysis.docx", generate_gap_analysis_word),
            ("process_flows", "Process Flow Documentation", "Process_Flows.docx", generate_process_flow_word),
            ("best_practices", "Industry Best Practices and Recommendations", "Best_Practices.docx", generate_best_practices_word),
            ("req_spec", "Master Requirement Specification", "Requirement_Spec.docx", generate_requirement_spec_word),
            ("process_mining", "Process Mining Analysis Report", "Process_Mining.docx", generate_process_mining_word),
        ]

        # Use ThreadPoolExecutor to run tasks in parallel (max 4 concurrent)
        new_docs = [None] * len(tasks)  # pre-allocate to preserve order
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_idx = {}
            for idx, (doc_id, doc_name, filename, gen_fn) in enumerate(tasks):
                fpath = os.path.join(out_dir, filename)
                future = executor.submit(
                    _generate_single_document,
                    gen_fn, kb, project_name, fpath, doc_id, doc_name,
                    existing_moms, idx, sid
                )
                future_to_idx[future] = idx

            # Wait for all tasks to complete (with per-task timeout)
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result(timeout=300)  # 5 minutes per document
                    new_docs[idx] = result
                except concurrent.futures.TimeoutError:
                    print(f"[ERROR] Task {tasks[idx][1]} timed out after 5 minutes")
                    new_docs[idx] = {
                        "id": tasks[idx][0],
                        "num": str(len(existing_moms) + idx + 1).zfill(2),
                        "name": tasks[idx][1],
                        "type": "consulting_doc",
                        "description": "Generation timed out after 5 minutes",
                        "file_path": None,
                        "status": "failed",
                        "approved": False,
                        "feedback": None
                    }
                except Exception as e:
                    print(f"[ERROR] Task {tasks[idx][1]} failed: {e}")
                    new_docs[idx] = {
                        "id": tasks[idx][0],
                        "num": str(len(existing_moms) + idx + 1).zfill(2),
                        "name": tasks[idx][1],
                        "type": "consulting_doc",
                        "description": f"Failed: {e}",
                        "file_path": None,
                        "status": "failed",
                        "approved": False,
                        "feedback": None
                    }
                # Update progress based on number of completed documents
                completed = sum(1 for d in new_docs if d is not None)
                pct = 12 + int((completed / len(tasks)) * 80)
                _emit(sid, pct, f"Generating documents", message=f"Completed {completed}/{len(tasks)} documents")

        # Filter out None (should not happen) and collect
        new_docs = [d for d in new_docs if d is not None]

        _emit(sid, 93, "Packaging documents", message="Creating ZIP package...")
        all_docs = existing_moms + new_docs
        zip_path = os.path.join(out_dir, "consulting_package.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for doc in all_docs:
                fp = doc.get("file_path")
                if fp and os.path.exists(fp):
                    zf.write(fp, os.path.basename(fp))

        generated = sum(1 for d in all_docs if d["status"] == "generated")
        store.update(sid,
                     status="reviewing",
                     documents=all_docs,
                     zip_path=zip_path,
                     progress=95,
                     current_step=f"Review ready — {generated}/{len(all_docs)} documents")
        _emit(sid, 95, "Documents ready for review", "reviewing",
              f"{generated} documents generated. Please review and approve.",
              data={"document_count": generated, "total": len(all_docs)})
        print(f"[DEBUG] Document generation finished. {generated}/{len(all_docs)} documents ready.")

    except Exception as e:
        print(f"[FATAL] Document generation failed for session {sid}: {e}")
        traceback.print_exc()
        store.update(sid, status="error", error=f"{e}\n{traceback.format_exc()}")
        _emit(sid, 0, "Error", "error", f"Generation failed: {e}")

def start_video_processing(sid, video_path, meeting_name):
    threading.Thread(target=process_single_video, args=(sid, video_path, meeting_name), daemon=True).start()

def start_document_generation(sid):
    threading.Thread(target=run_document_generation, args=(sid,), daemon=True).start()