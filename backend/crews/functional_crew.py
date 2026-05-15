"""
crews/functional_crew.py
-------------------------
CrewAI crew for functional consulting.
Uses LLM string names (not LangChain objects) to avoid pydantic validation errors.
Two modes:
  run_analysis()  -> requirements + clarifying questions
  run_enrichment() -> domain knowledge enrichment
Supports both Ollama and OpenAI (controlled by LLM_PROVIDER env var).
"""
import json,os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from json_utils import parse_json

def _get_llm_string():
    """Return model string for CrewAI (not LangChain object)."""
    provider=os.getenv("LLM_PROVIDER","ollama").lower()
    if provider=="openai":
        return os.getenv("OPENAI_MODEL","gpt-4.1-mini")  # updated to a good default
    # For Ollama: crewai uses "ollama/modelname" format
    model=os.getenv("LLM_MODEL","qwen2.5:14b")
    return f"ollama/{model}"

def _generate_questions(transcript_summary):
    """Generate clarifying questions using the configured LLM."""
    from video_processor import generate_text
    prompt=f"""You are a senior functional consultant reviewing a customer interview summary.
Generate 5-6 targeted clarifying questions to fill information gaps before creating consulting documents.
Focus on: production scale, existing systems, budget/timeline, compliance needs, integration complexity.

Interview summary: {transcript_summary[:3000]}

Return ONLY a JSON array of question strings."""
    result=generate_text(prompt,max_tokens=1000)
    qs=parse_json(result,fallback=[])
    if isinstance(qs,list) and len(qs)>=2:
        return qs
    return [
        "What is your current annual production capacity (MW/tons/units)?",
        "Which ERP/SCADA/MES systems are currently in use and which version?",
        "What is your target go-live timeline and total budget envelope?",
        "Are there specific regulatory or compliance requirements (ALMM, GMP, ISO, IEC)?",
        "How many production lines and distinct machine types need integration?",
        "How many operators and supervisors will use the system daily?",
    ]

def _extract_requirements(query):
    """Extract structured requirements using the configured LLM."""
    from video_processor import generate_text
    prompt=f"""You are a manufacturing pre-sales expert.
Extract structured requirements from this customer query.
Return ONLY a valid JSON object with these exact keys:
{{
  "industry": "e.g. Solar, Steel, Automotive",
  "product": "what they manufacture",
  "production_capacity": "number + unit",
  "lines": 2,
  "machine_types": 5,
  "erp": "ERP system name or null",
  "current_systems": ["list"],
  "pain_points": ["list of problems"],
  "requirements": ["list of functional needs"],
  "customization": "low or medium or high",
  "extra_notes": "anything else"
}}

Customer query: {query}"""
    result=generate_text(prompt,max_tokens=2000)
    return parse_json(result,fallback={
        "industry":"Manufacturing","product":"Unknown",
        "production_capacity":"N/A","lines":2,"machine_types":5,
        "erp":None,"current_systems":[],"pain_points":[],
        "requirements":[],"customization":"medium","extra_notes":""
    })

def _get_domain_knowledge(industry,context):
    """Get domain knowledge using the configured LLM."""
    from video_processor import generate_text
    prompt=f"""You are a {industry} manufacturing domain expert.
Based on the customer interviews below, provide:
1. Recommended MES modules and their value for {industry}
2. Key manufacturing process steps specific to {industry}
3. Integration patterns and protocols (OPC UA, SECS-GEM, REST etc.)
4. Compliance requirements (ALMM, IEC, ISO, GMP etc.)
5. ROI benchmarks: payback periods, OEE improvements, cost reductions
6. Common pain points and proven solutions for {industry}

Interview context: {context[:6000]}

Write a comprehensive summary (500+ words)."""
    return generate_text(prompt,max_tokens=3000)

class FunctionalCrew:
    """Functional consulting crew using direct LLM calls (OpenAI or Ollama)."""

    def __init__(self,customer_query,answers=None):
        self.query=customer_query
        self.answers=answers or {}
        if self.answers:
            qa="\n".join(f"Q: {q}\nA: {a}" for q,a in self.answers.items())
            self.enriched=f"{customer_query}\n\nCustomer clarifications:\n{qa}"
        else:
            self.enriched=customer_query

    def run_analysis(self):
        """Stage 1: Extract requirements + generate clarifying questions."""
        try:
            reqs=_extract_requirements(self.enriched)
            questions=_generate_questions(self.enriched)
            return {
                "requirements":reqs,
                "clarifying_questions":questions,
                "confidence_score":75,
                "gaps":["Verify production capacity","Confirm ERP version","Clarify compliance needs"]
            }
        except Exception as e:
            return {
                "requirements":{},"confidence_score":40,
                "clarifying_questions":[
                    "What is your current annual production capacity?",
                    "Which ERP system are you using and which version?",
                    "What is your target go-live timeline and budget?",
                    "Are there regulatory compliance requirements?",
                    "How many operators will use the system daily?",
                ],
                "gaps":[str(e)]
            }

    def run_domain_enrichment(self,industry,context):
        """Stage 2: Get deep domain knowledge for document enrichment."""
        try:
            domain_knowledge=_get_domain_knowledge(industry,context)
            return {"domain_knowledge":domain_knowledge,"success":True}
        except Exception as e:
            return {"domain_knowledge":"","success":False,"error":str(e)}