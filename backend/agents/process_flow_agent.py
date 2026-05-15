"""agents/process_flow_agent.py — Process Flows with AS-IS/TO-BE/Sequence diagrams -> Word."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from video_processor import generate_text
from knowledge_base import SessionKB
from pdf_styles.word_builder import WordBuilder
from pdf_styles.diagram_renderer import render_plantuml,clean_plantuml,validate_plantuml,ASIS_ACTIVITY,TOBE_ACTIVITY,SEQUENCE_DIAGRAM

def _gen_diagram(kb,out_dir,diagram_type,filename):
    ctx=kb.get_full_context(3000)
    if diagram_type=="asis":
        prompt=f"From these transcripts generate a PlantUML ACTIVITY diagram for the AS-IS current manual process.\nTranscripts: {ctx}\nRules: @startuml first line, @enduml last line, use start/stop/:/if/endif, no markdown.\nReturn ONLY valid PlantUML."
        fallback=ASIS_ACTIVITY
    elif diagram_type=="tobe":
        prompt=f"From these transcripts generate a PlantUML ACTIVITY diagram for the TO-BE future MES-enabled process.\nTranscripts: {ctx}\nRules: @startuml first line, @enduml last line, no markdown.\nReturn ONLY valid PlantUML."
        fallback=TOBE_ACTIVITY
    else:
        prompt=f"From these transcripts generate a PlantUML SEQUENCE diagram showing actors/systems interaction.\nTranscripts: {ctx}\nRules: @startuml first line, @enduml last line, use actor/participant/-->/->. No markdown.\nReturn ONLY valid PlantUML."
        fallback=SEQUENCE_DIAGRAM
    raw=generate_text(prompt,max_tokens=1500)
    code=clean_plantuml(raw)
    if not validate_plantuml(code): code=fallback
    return render_plantuml(code,output_dir=out_dir,filename=filename)

def _text(kb,project_name):
    context=kb.get_full_context(12000)
    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    system="You are a business process analyst. Document customer processes using ONLY interview data. Markdown."
    prompt=f"""Project: {project_name}\nSource: {meetings}
=== TRANSCRIPTS ===\n{context}

# Process Flow Documentation
**Project:** {project_name}

## 1. Process Inventory
[List all business processes identified from interviews]

## 2. AS-IS Process Flows Current State
For each process mentioned:
### 2.1 [Process Name]
**Owner:** | **Trigger:** | **Inputs:** | **Outputs:**
**Steps:** 1. [from transcript] 2. ...
**Pain Points:** - [issues mentioned]
**Cycle Time:** [if mentioned]

## 3. TO-BE Process Flows Future State with MES
### 3.1 [Process Name] Improved
**Changes:** [what changes with system]
**Steps:** 1. [new automated step] 2. ...
**Expected Benefits:** [time saved, errors reduced]

## 4. Process Comparison Summary
| Process | AS-IS Steps | TO-BE Steps | Time Saved | Automation Level |
|---------|-------------|-------------|------------|------------------|

## 5. Integration Points Between Processes
[Where processes hand off to each other or external systems]

## 6. Key Performance Indicators Process Level
| Process | KPI | Current | Target |
|---------|-----|---------|--------|

---
*Based on: {meetings}*"""
    return generate_text(prompt,system=system,max_tokens=8000)

def generate_process_flow_word(kb,project_name,output_path):
    out_dir=os.path.dirname(os.path.abspath(output_path))
    text=_text(kb,project_name)
    asis=_gen_diagram(kb,out_dir,"asis","asis_process.png")
    tobe=_gen_diagram(kb,out_dir,"tobe","tobe_process.png")
    seq=_gen_diagram(kb,out_dir,"sequence","sequence_diagram.png")
    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    wb=WordBuilder(project_name,"Process Flow Documentation",f"AS-IS / TO-BE | {meetings}")
    if asis:
        wb.add_heading("AS-IS Process Flow Current State")
        wb.add_image(asis,"Current State Process Flow",13)
    if tobe:
        wb.add_heading("TO-BE Process Flow Future State")
        wb.add_image(tobe,"Future State with MES",13)
    if seq:
        wb.add_heading("System Interaction Sequence Diagram")
        wb.add_image(seq,"Actor and System Sequence",14)
    wb.add_body(text)
    wb.add_footer_note(f"AI Functional Consultant | {project_name} | {meetings}")
    wb.save(output_path)
    return text
