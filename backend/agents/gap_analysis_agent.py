"""agents/gap_analysis_agent.py — Full Gap Analysis with all 10 sections -> Word + diagram."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from video_processor import generate_text
from knowledge_base import SessionKB
from pdf_styles.word_builder import WordBuilder
from pdf_styles.diagram_renderer import render_plantuml

_GAP_DIAG="""@startuml
skinparam backgroundColor #FAFAFA
title Gap Analysis Priority Matrix
rectangle "CRITICAL Must Fix" as c #FDECEA {
  card "No Equipment Integration" as g1
  card "No Real-time Traceability" as g2
}
rectangle "HIGH PRIORITY" as h #FFF3CD {
  card "Manual SPC" as g3
  card "No OEE Dashboard" as g4
  card "ERP-MES Disconnect" as g5
}
rectangle "MEDIUM PRIORITY" as m #D4EDDA {
  card "Manual Reporting" as g6
  card "No Predictive Maintenance" as g7
}
note right of c : Blocks go-live\\nMust fix before launch
note right of h : Major efficiency loss\\nFix in Phase 1-2
note right of m : Improvement opportunity\\nFix in Phase 2-3
@enduml"""

def _text(kb,project_name):
    context=kb.get_full_context(14000)
    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    system=("You are a senior business process consultant. Write a complete Gap Analysis "
            "with all 10 required sections per ISA-95 and SEMI PV2 standards. "
            "Use ONLY interview data. Markdown format.")
    prompt=f"""Project: {project_name}\nSource: {meetings}
=== MEETING KNOWLEDGE BASE ===\n{context}

# Gap Analysis Report
**Project:** {project_name}  **Version:** 1.0  **Standard:** ISA-95 / SEMI PV2 / MESA

## 1. Document Header and Scope
**Project:** {project_name}
**Scope:** [Which processes, systems, departments covered from interviews]
**Reference Standard:** ISA-95 Level 3, SEMI PV2, MESA MES Framework
**Assumptions and Limitations:** [Areas excluded or data not available]

## 2. Baseline Summary AS-IS
[Current state — manual vs automated, existing systems, key pain points from interviews]

**Current Systems Identified:**
| System | Type | Coverage | Limitations |
|--------|------|----------|-------------|

**Key Baseline Metrics:**
| Metric | Current Value | Source |
|--------|--------------|--------|
| OEE | [from interview or Not captured] | |
| First Pass Yield | ... | |
| Traceability Depth | ... | |

## 3. Target Reference Model TO-BE Best Practice
**Reference Standard:** ISA-95 Level 3 MES Functions, SEMI PV2 for solar

**Ideal Capabilities by Process Area:**
| Process Area | Ideal Capability Best Practice |
|-------------|-------------------------------|
| Production Tracking | Real-time WIP tracking, OEE dashboards |
| Quality Management | Real-time SPC, automated defect classification |
| Equipment Integration | SECS/GEM or OPC UA for all equipment |
| Traceability | Single-wafer/unit tracking from input to output |
| Planning and Scheduling | APS with finite capacity, real-time re-scheduling |

## 4. Gap Analysis Matrix Core Table
| Gap-ID | Capability | As-Is Description | To-Be Best Practice | Gap Type | Impact | Priority | Recommended Action |
|--------|-----------|-------------------|---------------------|----------|--------|----------|--------------------|
| GAP-001 | [from interviews] | [current state] | [best practice] | Missing / Partial / Inefficient / No Integration | High/Med/Low | Critical/High/Med/Low | [action] |
[Extract ALL gaps from interviews — minimum 8-10 rows]

Gap Types: Missing capability | Partial capability | Inefficient process | No integration | No standard

## 5. Gap Categorization and Prioritization
| Priority | Definition | Gaps in this category |
|----------|------------|----------------------|
| Critical Must Fix | Blocks go-live, compliance risk, financial loss | [Gap IDs] |
| High | Major efficiency or quality loss | [Gap IDs] |
| Medium | Improvement opportunity, can be post-launch | [Gap IDs] |
| Low | Nice to have | [Gap IDs] |

## 6. Impact Analysis
| Gap-ID | Operational Impact | Quality Impact | Cost Impact | Compliance Risk |
|--------|-------------------|----------------|-------------|-----------------|
| GAP-001 | [e.g. 2 hrs/day manual work] | [e.g. 3% lower yield] | [e.g. rework cost] | [e.g. IEC audit risk] |

## 7. Recommended Actions and Solutions
| Gap-ID | Recommended Action | Estimated Effort | Owner | Target Phase |
|--------|-------------------|-----------------|-------|--------------|
| GAP-001 | [specific action] | [weeks] | [team] | Phase 1/2/3 |

## 8. Risk and Dependency Log
**Risks if gaps not closed:**
| Risk | Gap-ID | Probability | Impact | Mitigation |
|------|--------|-------------|--------|------------|

**Dependencies:**
| Dependency | Gap-ID | Prerequisite |
|------------|--------|-------------|

## 9. Summary of Key Findings and Next Steps
**Top 5 Critical Gaps:**
1. [Gap-ID]: [description and business case]
2. [Gap-ID]: ...
3. [Gap-ID]: ...
4. [Gap-ID]: ...
5. [Gap-ID]: ...

**Recommended Phased Roadmap:**
- Phase 1 0-3 months: [quick wins and critical fixes]
- Phase 2 3-9 months: [structural changes]
- Phase 3 9-18 months: [advanced capabilities]

**Immediate Action Items:**
| # | Action | Owner | Deadline |
|---|--------|-------|----------|

## 10. Appendices
[Reference to interview notes, process diagrams, equipment list, screenshots]

---
*Based on: {meetings} | Reference: ISA-95, SEMI PV2, MESA*"""
    return generate_text(prompt,system=system,max_tokens=10000)

def generate_gap_analysis_word(kb,project_name,output_path):
    out_dir=os.path.dirname(os.path.abspath(output_path))
    gap_text=_text(kb,project_name)

    diag = None
    try:
        diag = render_plantuml(_GAP_DIAG, output_dir=out_dir, filename="gap_priority_matrix.png")
    except Exception as e:
        print(f"Warning: Gap diagram failed: {e}")

    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    wb=WordBuilder(project_name,"Gap Analysis Report",f"AS-IS vs TO-BE | ISA-95 | {meetings}")
    wb.add_callout("Gap Analysis covers all 10 required sections...", color="FFFBEB", border_color="D97706")

    if diag:
        wb.add_heading("Gap Priority Matrix")
        wb.add_image(diag,"Gap Analysis Priority Matrix",14)
    else:
        wb.add_body("*Note: Gap priority matrix diagram could not be generated (network timeout).*")

    wb.add_body(gap_text)
    wb.add_footer_note(f"AI Functional Consultant | {project_name} | ISA-95, SEMI PV2, MESA")
    wb.save(output_path)
    return gap_text
