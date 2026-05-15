"""agents/frd_agent.py — Functional Requirements Document with all required sections -> Word."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from video_processor import generate_text
from knowledge_base import SessionKB
from pdf_styles.word_builder import WordBuilder

def _text(kb,project_name):
    context=kb.get_full_context(15000)
    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    system=("You are a senior functional consultant writing a complete FRD. "
            "Include unique IDs, pre/post conditions, triggers, inputs/outputs, "
            "business rules, error handling, dependencies, priority, and acceptance criteria. "
            "Use ONLY customer interview data. Markdown.")
    prompt=f"""Project: {project_name}\nSource: {meetings}
=== MEETING KNOWLEDGE BASE ===\n{context}

# Functional Requirements Document
**Project:** {project_name}  **Version:** 1.0  **Status:** Draft

## Document Control
| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | Today | AI Functional Consultant | Initial draft from customer interviews |

## Revision History
| Version | Change Description | Impact |
|---------|--------------------|--------|

## 1. Introduction
### 1.1 Purpose
[What this FRD covers and why]
### 1.2 Scope
[System boundary — in and out of scope]
### 1.3 Audience
[Who should read this document]

## 2. Glossary of Terms
| Term | Definition |
|------|------------|
[Every domain-specific term from interviews]

## 3. Assumptions and Constraints
| ID | Type | Description | Impact |
|----|------|-------------|--------|
| ASM-001 | Business | ... | |
| CON-001 | Technical | ... | |

## 4. System Overview
[What system needs to be built from interviews]

## 5. User Roles and Personas
| Role | Description | Key Needs | Access Level |
|------|-------------|-----------|--------------|
[Every user type mentioned]

## 6. Functional Requirements

### 6.1 [Module Name from interviews]

#### FR-MOD-001: [Requirement Name]
- **Description:** The system SHALL [single testable statement]
- **Pre-Conditions:** [what must be true before]
- **Post-Conditions:** [what must be true after]
- **Trigger:** [what initiates this function]
- **Inputs:**
  | Field | Type | Format | Required | Validation |
  |-------|------|--------|----------|------------|
- **Outputs:**
  | Field | Type | Description |
  |-------|------|-------------|
- **Business Rules:** [calculations, validations, decision logic]
- **Error Handling:** [what happens when things go wrong]
- **Dependencies:** [other requirements this depends on]
- **Priority:** Must Have / Should Have / Could Have / Won't Have
- **Acceptance Criteria:**
  - AC1: Given [...] When [...] Then [...]
  - AC2: Given [...] When [...] Then [...]

### 6.2 [Next Module]
[Continue for all modules from interviews]

## 7. Integration Requirements
| INT-ID | Source System | Target System | Data Exchanged | Protocol | Frequency |
|--------|--------------|--------------|----------------|----------|-----------|
| INT-001 | SAP ERP | MES | Production Orders | REST/IDoc | Real-time |

## 8. Data Requirements
| DAT-ID | Data Entity | Source | Owner | Retention | Quality Rules |
|--------|------------|--------|-------|-----------|---------------|

## 9. Reporting and Analytics Requirements
| REP-ID | Report Name | Content | Frequency | Audience |
|--------|------------|---------|-----------|----------|

## 10. Non-Functional Requirements
| NFR-ID | Category | Requirement | Metric | Priority |
|--------|----------|-------------|--------|----------|
| NFR-001 | Performance | System response time | < 3 seconds | Must Have |
| NFR-002 | Availability | Uptime during production | 99.5% | Must Have |
| NFR-003 | Security | Role-based access control | Per role matrix | Must Have |
| NFR-004 | Scalability | Support future line expansion | 2x growth | Should Have |

## 11. Traceability Matrix
| Business Req BR-ID | Functional Req FR-ID | Test Case | Status |
|---------------------|----------------------|-----------|--------|

## 12. Open Issues and Questions
| # | Question | Raised In | Owner | Status |
|---|----------|-----------|-------|--------|

---
*Based on: {meetings}*"""
    return generate_text(prompt,system=system,max_tokens=12000)

def generate_frd_word(kb,project_name,output_path):
    frd_text=_text(kb,project_name)
    meetings=", ".join(m["name"] for m in kb.get_info()["meetings"]) or "interviews"
    wb=WordBuilder(project_name,"Functional Requirements Document",f"FRD v1.0 | {meetings}")
    wb.add_callout("This FRD includes: Unique IDs, Pre/Post conditions, Triggers, "
                   "Inputs/Outputs, Business Rules, Error Handling, Dependencies, "
                   "Priority (MoSCoW), and Acceptance Criteria for every requirement.",
                   color="F0FDFA",border_color="0F766E")
    wb.add_body(frd_text)
    wb.add_footer_note(f"AI Functional Consultant | {project_name} | FRD v1.0 | Confidential")
    wb.save(output_path)
    return frd_text
