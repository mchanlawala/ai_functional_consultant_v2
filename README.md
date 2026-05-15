# AI Functional Consultant v2.0

Multi-agent AI system: MP4 customer interviews → MoM → Knowledge Base → 8 Word documents with diagrams.

## Quick Start
```bash
cd fc_v3/backend
pip install -r requirements.txt
cp .env.example .env
ollama pull llama3.2:latest && ollama pull llava:latest && ollama pull nomic-embed-text
python server.py
```
Open `frontend/public/index.html` in browser.

## Workflow
1. Create Session → 2. Upload MP4(s) → 3. Generate Documents → 4. Review & Approve → 5. Download ZIP

## Documents Generated
- MoM per meeting (Word)     - BRD (Word + context diagram)
- FRD with all sections       - Gap Analysis (Word + priority matrix)
- Process Flows (Word + AS-IS/TO-BE/Sequence diagrams)
- Best Practices (Word + maturity model diagram)
- Process Mining Report       - Master Requirement Specification
