"""agents/requirement_spec_agent.py — Master Requirement Specification -> Word."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from video_processor import generate_text
from knowledge_base import SessionKB
from pdf_styles.word_builder import WordBuilder

def _text(kb,project_name):
    context=kb.get_full_context(15000)
    info=kb.get_info()
    meetings=", ".join(m["name"] for m in info["meetings"]) or "interviews"
    system=("You are a principal functional consultant writing a master Requirement Specification. "
            "This is the definitive document. Be comprehensive and traceable. Markdown.")
    prompt=f"""Project: {project_name}\nSource: {meetings}\nMeetings: {len(info['meetings'])} | KB chunks: {info['total_chunks']}
=== KNOWLEDGE BASE ===\n{context}

# Master Requirement Specification
**Project:** {project_name}  **Version:** 1.0  **Status:** Draft

## Document Control
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Today | AI Functional Consultant | Initial from {len(info['meetings'])} interviews |

## 1. Executive Summary
[3-4 paragraphs: project context, objectives, scope, key decisions from interviews]

## 2. Project Objectives
[SMART objectives derived from customer interviews]

## 3. Stakeholders and Roles
| Stakeholder | Role | Responsibilities | Interview Participation |
|-------------|------|-----------------|------------------------|

## 4. Requirements Catalogue

### 4.1 Business Requirements
| REQ-ID | Category | Requirement | Priority | Source | Status |
|--------|----------|-------------|----------|--------|--------|
| BR-001 | Process | ... | Must Have | [meeting] | Open |
[ALL business requirements from ALL meetings]

### 4.2 Functional Requirements
| REQ-ID | Module | Requirement | User Story | Acceptance Criteria | Priority |
|--------|--------|-------------|------------|---------------------|----------|
| FR-001 | ... | ... | As a... | Given...When...Then... | Must Have |

### 4.3 Non-Functional Requirements
| REQ-ID | Type | Requirement | Metric |
|--------|------|-------------|--------|
| NFR-001 | Performance | ... | [measurable target] |
| NFR-002 | Security | ... | |
| NFR-003 | Availability | ... | |
| NFR-004 | Scalability | ... | |

### 4.4 Integration Requirements
| INT-ID | Source System | Target System | Data | Method | Frequency |
|--------|--------------|--------------|------|--------|-----------|

### 4.5 Data Requirements
| DAT-ID | Data Entity | Source | Owner | Retention | Quality Rules |
|--------|------------|--------|-------|-----------|---------------|

## 5. Process Requirements
[Key processes and their requirements from interviews]

## 6. Traceability Matrix
| Business Req | Functional Req | Process | Test Case |
|-------------|----------------|---------|-----------|

## 7. Constraints and Assumptions
| ID | Type | Description | Impact |
|----|------|-------------|--------|
| CON-001 | Technical | ... | |
| ASM-001 | Business | ... | |

## 8. Risks and Dependencies
| Risk / Dependency | Probability | Impact | Mitigation |
|-------------------|-------------|--------|------------|

## 9. Glossary
[Terms and definitions from the customer domain]

## 10. Open Issues and Questions
| # | Question | Raised In | Raised By | Status |
|---|----------|-----------|-----------|--------|

## 11. Next Steps
[Recommended next actions based on interviews]

---
*Master specification from {len(info['meetings'])} customer interviews: {meetings}*"""
    return generate_text(prompt,system=system,max_tokens=12000)

def generate_requirement_spec_word(kb,project_name,output_path):
    text=_text(kb,project_name)
    info=kb.get_info()
    meetings=", ".join(m["name"] for m in info["meetings"]) or "interviews"
    wb=WordBuilder(project_name,"Master Requirement Specification",
                   f"RSP v1.0 | {len(info['meetings'])} meetings | {meetings}")
    wb.add_callout(f"Master specification compiled from {len(info['meetings'])} customer interviews "
                   f"with {info['total_chunks']} knowledge base chunks. "
                   "Contains: Business Requirements, Functional Requirements, NFRs, "
                   "Integrations, Data Requirements, Traceability Matrix.",
                   color="EFF6FF",border_color="2563EB")
    wb.add_body(text)
    wb.add_footer_note(f"AI Functional Consultant | {project_name} | Master RSP v1.0 | Confidential")
    wb.save(output_path)
    return text
