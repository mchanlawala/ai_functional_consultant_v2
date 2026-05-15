"""agents/best_practices_agent.py — Industry Best Practices -> Word + maturity diagram."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from video_processor import generate_text
from knowledge_base import SessionKB
from pdf_styles.word_builder import WordBuilder
from pdf_styles.diagram_renderer import render_plantuml

_MATURITY="""@startuml
skinparam backgroundColor #FAFAFA
title Manufacturing Digital Maturity Model
rectangle "Level 1 Initial" as l1 #FDECEA
rectangle "Level 2 Managed" as l2 #FFF3CD
rectangle "Level 3 Defined" as l3 #EFF6FF
rectangle "Level 4 Quantified" as l4 #D4EDDA
rectangle "Level 5 Optimising" as l5 #F0FDFA
l1 -right-> l2 : Manual to Tracked
l2 -right-> l3 : Tracked to Standardised
l3 -right-> l4 : Standardised to Measured
l4 -right-> l5 : Measured to AI-Optimised
note bottom of l1 : Paper / Excel\nNo visibility
note bottom of l3 : MES deployed\nOEE tracked
note bottom of l5 : AI/ML predictive\nAutonomous ops
@enduml"""

def _text(kb,project_name):
    context=kb.get_full_context(12000)
    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    system=("You are a senior functional consultant. Map customer situation to industry best practices. "
            "Reference ISA-95, SEMI PV2, MESA, IEC standards. Markdown.")
    prompt=f"""Project: {project_name}\nSource: {meetings}
=== TRANSCRIPTS ===\n{context}

# Industry Best Practices and Recommendations
**Project:** {project_name} | **Framework:** ISA-95 / SEMI PV2 / MESA / IEC

## 1. Customer Industry Context
[Summarise industry, domain, and maturity from interviews]

## 2. Applicable Industry Standards and Frameworks
| Standard / Framework | Relevance | Key Requirements for Customer |
|---------------------|-----------|-------------------------------|
| ISA-95 IEC 62264 | MES functional model | Level 3 functions: production, quality, inventory |
| SEMI PV2 PVECI | Solar equipment interface | SECS/GEM or OPC UA for all PV tools |
| MESA MES Framework | MES best practices | 11 MES functions mapping |
| IEC 62904 | PV traceability | Module-level serial traceability |
| ISO 9001 | Quality management | SPC, FMEA, control plan |
[Add others from interviews]

## 3. Best Practice Recommendations by Area

### 3.1 Production Operations ISA-95 Level 3
| Customer Approach | Industry Best Practice | Gap | Recommendation |
|------------------|----------------------|-----|----------------|

### 3.2 Quality Management
| Customer Approach | Best Practice | Recommendation |
|------------------|--------------|----------------|

### 3.3 Equipment Integration and Data Collection
| Protocol | Customer Status | Best Practice | Priority |
|----------|----------------|---------------|----------|
| SECS/GEM | [from interview] | Mandatory for new tools | High |
| OPC UA | [from interview] | For legacy tools | High |
| REST API | [from interview] | For modern sorters | Medium |

### 3.4 Traceability and Genealogy
[Best practices for the customer product type]

### 3.5 KPIs and Performance Benchmarks
| KPI | Industry Benchmark | Customer Current | Target | Improvement |
|-----|-------------------|-----------------|--------|-------------|
| OEE | >85% world class | [from interview] | 85%+ | +X% |
| First Pass Yield | >98% | [from interview] | 98%+ | |
| Cycle Time | [benchmark] | [from interview] | | |

## 4. Digital Maturity Assessment
| Dimension | Current Level 1-5 | Target Level | Gap | Actions |
|-----------|-------------------|-------------|-----|---------|
| Production Tracking | | | | |
| Quality Management | | | | |
| Equipment Integration | | | | |
| Analytics and Reporting | | | | |
| Predictive Capabilities | | | | |

## 5. Automation Opportunities
| Process | Current State | Automation Type | Technology | ROI Estimate |
|---------|--------------|-----------------|------------|--------------|

## 6. Recommended Technology Stack
[Specific tools, platforms, integrations for their domain]

## 7. Phased Implementation Roadmap
### Phase 1 Foundation 0-6 months
[Quick wins: basic MES, equipment integration, traceability]
### Phase 2 Optimisation 6-18 months
[Advanced: SPC, OEE, predictive quality]
### Phase 3 Intelligence 18+ months
[AI/ML: predictive maintenance, yield optimisation, digital twin]

## 8. Change Management Considerations
[People, process, technology change factors]

---
*Based on: {meetings} | Standards: ISA-95, SEMI PV2, MESA*"""
    return generate_text(prompt,system=system,max_tokens=8000)

def generate_best_practices_word(kb,project_name,output_path):
    out_dir=os.path.dirname(os.path.abspath(output_path))
    text=_text(kb,project_name)
    diag=render_plantuml(_MATURITY,output_dir=out_dir,filename="maturity_model.png")
    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    wb=WordBuilder(project_name,"Industry Best Practices and Recommendations",f"ISA-95 / SEMI PV2 / MESA | {meetings}")
    if diag:
        wb.add_heading("Digital Maturity Model")
        wb.add_image(diag,"Manufacturing Digital Maturity Model",13)
    wb.add_body(text)
    wb.add_footer_note(f"AI Functional Consultant | {project_name} | ISA-95, SEMI PV2, MESA")
    wb.save(output_path)
    return text
