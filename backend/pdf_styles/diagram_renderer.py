"""pdf_styles/diagram_renderer.py — PlantUML diagrams via Kroki."""
import os, re, requests
KROKI_URL = "https://kroki.io/plantuml/png"
OUTPUTS_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)),"data","outputs")

def render_plantuml(code, output_dir=None, filename="diagram.png"):
    out=output_dir or OUTPUTS_BASE; os.makedirs(out,exist_ok=True)
    path=os.path.join(out,filename)
    try:
        r=requests.post(KROKI_URL,json={"diagram_source":code},timeout=30)
        if r.status_code==200:
            with open(path,"wb") as f: f.write(r.content)
            return path
    except Exception as e: print(f"Diagram failed: {e}")
    return None

def validate_plantuml(code):
    lines=[l.strip() for l in code.splitlines() if l.strip()]
    return bool(lines) and lines[0].startswith("@startuml") and lines[-1].startswith("@enduml")

def clean_plantuml(text):
    text=re.sub(r"```[a-z]*\n?","",text); text=re.sub(r"\n?```","",text).strip()
    m=re.search(r"(@startuml.*?@enduml)",text,re.DOTALL)
    return m.group(1).strip() if m else text

ASIS_ACTIVITY="""@startuml
skinparam backgroundColor #FAFAFA
title AS-IS Process (Current State - Manual)
start
:Customer Interview;
:Manual Process Mapping (Excel/Paper);
:Requirements Collection;
:Manual Gap Identification;
:Document Preparation;
:Email Review and Approval;
stop
@enduml"""

TOBE_ACTIVITY="""@startuml
skinparam backgroundColor #FAFAFA
title TO-BE Process (Future State with MES)
start
:MP4 Interview Upload;
:AI Transcription via Whisper;
:Knowledge Base Build via RAG;
:CrewAI Multi-Agent Analysis;
:Auto-Generated Documents;
:Review and Approve via Portal;
:Publish Package;
stop
@enduml"""

SEQUENCE_DIAGRAM="""@startuml
skinparam backgroundColor #FAFAFA
title Functional Consulting AI Workflow
actor "Customer" as C
participant "Functional Consultant" as FC
participant "AI Orchestrator" as AI
participant "Knowledge Base RAG" as KB
participant "Document Generator" as DG
C -> FC : Customer interviews MP4
FC -> AI : Upload recordings
AI -> AI : Whisper transcription
AI -> AI : LLaVA screen analysis
AI -> KB : Build vector knowledge base
AI -> FC : Generate MoM per meeting
FC -> C : Review and confirm MoM
AI -> KB : Query domain knowledge
AI -> DG : Generate all documents
DG -> FC : Review portal
FC -> C : Present and publish package
@enduml"""

PROCESS_FLOW_DIAGRAM="""@startuml
skinparam backgroundColor #FAFAFA
skinparam component {BackgroundColor #EFF6FF BorderColor #2563EB}
title AI Functional Consulting Document Pipeline
package "Input Layer" {component "MP4 Recordings" as mp4}
package "Processing Layer" {
  component "Whisper Transcription" as wh
  component "LLaVA Screen Analysis" as lv
  component "MoM Generator" as mom
}
package "Knowledge Layer" {
  component "ChromaDB Vector Store" as kb
  component "CrewAI Orchestrator" as crew
}
package "Document Layer" {
  component "BRD Agent" as brd
  component "FRD Agent" as frd
  component "Gap Analysis Agent" as gap
  component "Process Flow Agent" as pf
  component "Best Practices Agent" as bp
  component "Req Spec Agent" as rs
}
package "Output Layer" {component "Word Documents Package" as out}
mp4-->wh; mp4-->lv; wh-->mom; lv-->mom; mom-->kb
kb-->crew; crew-->brd; crew-->frd; crew-->gap
crew-->pf; crew-->bp; crew-->rs
brd-->out; frd-->out; gap-->out; pf-->out; bp-->out; rs-->out
@enduml"""
