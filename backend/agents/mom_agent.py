"""agents/mom_agent.py — Minutes of Meeting -> Word document (enhanced with KB)."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from video_processor import generate_text
from pdf_styles.word_builder import WordBuilder
from knowledge_base import get_kb

def generate_mom(transcript, screen_descs, meeting_name, project_name="Project", kb=None):
    screen = "\n".join(screen_descs) if screen_descs else "No screen analysis."
    context = ""
    if kb:
        # Pull relevant past context to fill gaps
        context = kb.get_full_context(4000)
        context = f"\n=== PRIOR KNOWLEDGE BASE CONTEXT ===\n{context}\n"

    t = transcript[:12000]
    system = ("You are a professional meeting secretary. Write accurate MoM STRICTLY from "
              "the audio transcript and any prior context. Do NOT invent information not present. "
              "If a field is truly missing, write 'Not mentioned in recording'. Markdown.")
    prompt = f"""Meeting: {meeting_name}
Project: {project_name}
=== AUDIO TRANSCRIPT ===
{t}
=== SCREEN RECORDING ANALYSIS ===
{screen}
{context}

Write Minutes of Meeting:
# Minutes of Meeting — {meeting_name}
## Meeting Details
- **Date:** [extract or "Not mentioned"]
- **Time:** [extract or "Not mentioned"]
- **Duration:** [estimate from transcript length]
- **Attendees:** [every name/role mentioned – if none, write "No attendees identified"]
- **Facilitator:** [who led – if unknown, "Not specified"]
- **Platform:** [Teams/Zoom/in-person – if unknown, "Not specified"]
## Purpose and Agenda
[2-3 sentences – what this session was about]
## Key Discussion Points
[Every topic discussed – direct from transcript]
## Business Processes Discussed
[Any processes, workflows, or systems mentioned]
## Pain Points and Challenges Raised
[Problems the customer described]
## Requirements Mentioned
[Any requirements or desired features]
## Decisions Made
[Concrete decisions, or "No formal decisions recorded"]
## Action Items
| # | Action | Owner | Deadline | Status |
|---|--------|-------|----------|--------|
[Extract from transcript – if none, write "No action items recorded"]
## Screen Activity Summary
[What was shown on screen with timestamps]
## Next Steps
[Follow-up actions]
---
*Generated from: {meeting_name} | Transcript: {len(transcript)} chars | Frames: {len(screen_descs)}*"""
    return generate_text(prompt, system=system, max_tokens=8192)

def generate_mom_word(transcript, screen_descs, meeting_name, project_name, output_path, session_id=None):
    kb = get_kb(session_id) if session_id else None
    mom_text = generate_mom(transcript, screen_descs, meeting_name, project_name, kb)
    wb = WordBuilder(project_name, f"Minutes of Meeting", f"{meeting_name}")
    wb.add_body(mom_text)
    wb.add_footer_note(f"AI Functional Consultant | {meeting_name} | Transcript: {len(transcript)} chars | Frames: {len(screen_descs)}")
    wb.save(output_path)
    return mom_text