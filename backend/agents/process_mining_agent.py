"""agents/process_mining_agent.py — AI Process Mining Report -> Word."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from video_processor import generate_text
from knowledge_base import SessionKB
from pdf_styles.word_builder import WordBuilder
from pdf_styles.diagram_renderer import render_plantuml,PROCESS_FLOW_DIAGRAM

def _text(kb,project_name):
    context=kb.get_full_context(13000)
    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    system=("You are an AI Process Mining analyst. Analyse meeting transcripts to discover, "
            "map and analyse business processes. Identify inefficiencies, bottlenecks, "
            "variants and automation opportunities. Markdown.")
    prompt=f"""Project: {project_name}\nSource: {meetings}
=== TRANSCRIPTS ===\n{context}

# Process Mining Analysis Report
**Project:** {project_name}

## 1. Executive Summary
[Key process discoveries from the interviews]

## 2. Discovered Processes
[All business processes identified through transcript analysis]

## 3. Process Analysis
For each discovered process:
### 3.1 [Process Name]
**Frequency:** [how often mentioned]
**Participants:** [roles involved]
**Systems Touched:** [applications used]
**Estimated Duration:** [time taken]
**Variants:**
- Happy path: [standard flow]
- Variant 1: [exception]
- Variant 2: [alternative]

## 4. Bottleneck Analysis
| Process | Bottleneck Location | Root Cause | Frequency | Impact |
|---------|-------------------|------------|-----------|--------|

## 5. Process Inefficiencies
| Inefficiency | Process | Current Impact | Effort to Fix | Priority |
|-------------|---------|---------------|---------------|----------|
| Manual data entry | ... | 2 hrs/day | Low | High |

## 6. Rework and Waste Identification
[Activities that are repeated, redundant or non-value-adding]

## 7. Conformance Analysis
| Process | Expected Flow | Actual Flow from interviews | Deviation |
|---------|-------------|----------------------------|-----------|

## 8. Automation Opportunity Map
| Process Step | Current State | Automation Type | Technology | ROI Estimate |
|-------------|--------------|-----------------|------------|--------------|

## 9. Process Performance Metrics Target
| Process | KPI | Current | Target | Improvement |
|---------|-----|---------|--------|-------------|

## 10. Process Mining Recommendations
### Priority 1 Immediate Automation Candidates
### Priority 2 Process Redesign Needed
### Priority 3 Monitoring and Control Improvements

---
*Process mining from: {meetings}*"""
    return generate_text(prompt,system=system,max_tokens=8000)

def generate_process_mining_word(kb,project_name,output_path):
    out_dir=os.path.dirname(os.path.abspath(output_path))
    text=_text(kb,project_name)
    diag=render_plantuml(PROCESS_FLOW_DIAGRAM,output_dir=out_dir,filename="pipeline_diagram.png")
    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    wb=WordBuilder(project_name,"Process Mining Analysis Report",f"AI Process Discovery | {meetings}")
    if diag:
        wb.add_heading("AI Document Generation Pipeline")
        wb.add_image(diag,"Functional Consulting AI Pipeline",14)
    wb.add_body(text)
    wb.add_footer_note(f"AI Functional Consultant | {project_name} | Process Mining Report")
    wb.save(output_path)
    return text
