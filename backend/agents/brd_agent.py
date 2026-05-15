"""agents/brd_agent.py — Business Requirements Document -> Word + context diagram."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from video_processor import generate_text
from knowledge_base import SessionKB
from pdf_styles.word_builder import WordBuilder
from pdf_styles.diagram_renderer import render_plantuml,clean_plantuml,validate_plantuml

def _text(kb,project_name):
    context=kb.get_full_context(15000)
    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    system=("You are a senior business analyst. Write a professional BRD "
            "using ONLY customer interview information. Markdown format.")
    prompt=f"""Project: {project_name}\nSource: {meetings}
=== KNOWLEDGE BASE ===\n{context}

# Business Requirements Document
**Project:** {project_name}  **Version:** 1.0  **Source:** {meetings}

## 1. Executive Summary
[2-3 paragraphs from interviews — what customer wants to achieve and why]

## 2. Business Context and Background
[Current state — industry, scale, how they operate today]

## 3. Business Objectives
[Numbered list of concrete business goals from interviews]

## 4. Scope
### 4.1 In Scope
[Items explicitly requested]
### 4.2 Out of Scope
[Items explicitly excluded]

## 5. Stakeholders
| Stakeholder | Role | Interest and Concerns |
|-------------|------|-----------------------|
[From meetings]

## 6. Business Requirements
### 6.1 Functional Requirements
| ID | Requirement | Priority | Source Meeting |
|----|-------------|----------|----------------|
| BR-001 | ... | High/Med/Low | [meeting] |

### 6.2 Non-Functional Requirements
| ID | Category | Requirement |
|----|----------|-------------|
| NFR-001 | Performance | ... |
| NFR-002 | Security | ... |
| NFR-003 | Scalability | ... |

## 7. Current Process Analysis AS-IS
[How customer works today from interviews]

## 8. Desired Future Process TO-BE
[How customer wants to work after implementation]

## 9. Gap Summary
| Area | AS-IS | TO-BE | Gap |
|------|-------|-------|-----|

## 10. Assumptions and Constraints
[From interviews]

## 11. Acceptance Criteria
[How customer will verify requirements are met]

---
*Based on customer interviews: {meetings}*"""
    return generate_text(prompt,system=system,max_tokens=10000)

def _context_diagram(kb,out_dir):
    ctx=kb.get_full_context(3000)
    prompt=f"""From these transcripts generate a PlantUML component diagram showing system context.
Transcripts: {ctx}
Rules: First line @startuml, last line @enduml. Use component/actor/-->. No markdown fences.
Return ONLY valid PlantUML."""
    raw=generate_text(prompt,max_tokens=1500)
    code=clean_plantuml(raw)
    if not validate_plantuml(code):
        code="""@startuml
skinparam backgroundColor #FAFAFA
actor "Customer Users" as user
component "MES Platform" as mes
component "SAP ERP" as erp
component "Quality Lab" as qlab
component "Production Machines" as machines
user --> mes : Operate
mes --> erp : Orders and Confirmations
mes --> machines : OPC UA / SECS-GEM
machines --> mes : Sensor Data
qlab --> mes : Test Results
@enduml"""
    return render_plantuml(code,output_dir=out_dir,filename="brd_context.png")

def generate_brd_word(kb, project_name, output_path):
    out_dir = os.path.dirname(os.path.abspath(output_path))
    brd_text = _text(kb, project_name)

    # Try to generate diagram, but don't block if it fails
    diag = None
    try:
        diag = _context_diagram(kb, out_dir)
    except Exception as e:
        print(f"Warning: Could not generate context diagram: {e}")

    meetings = ", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    wb = WordBuilder(project_name, "Business Requirements Document", f"BRD v1.0 | {meetings}")

    if diag:
        wb.add_heading("System Context Diagram")
        wb.add_image(diag, "System Context Overview", 14)
    else:
        # Use add_body instead of add_paragraph
        wb.add_body("*Note: System context diagram could not be generated (network timeout).*")

    wb.add_body(brd_text)
    wb.add_footer_note(f"AI Functional Consultant | {project_name} | {meetings}")
    wb.save(output_path)
    return brd_text
