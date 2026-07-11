# ClaimGuard AI — Master Prompt & Architecture Document
### Agentic Health Insurance Claims Triage & Prior-Authorization RAG Assistant (UAE Market)

**Prepared for:** Krishna Mathur — MAIB, SP Jain Dubai (AS25DXB018)
**Purpose:** Hand this document to an agentic coding tool (Claude Code) as the single source of truth to build ClaimGuard AI end-to-end. Every section below is a direct build instruction — follow it in order.
**Status:** Portfolio / recruiter-facing project. Entirely synthetic data. Not for production or real patient use.

---

## 0. HOW TO USE THIS DOCUMENT (instructions to the coding agent)

You are building ClaimGuard AI, a multi-agent, RAG-grounded health insurance claims triage system for the UAE market. Build in the phase order given in Section 10. Do not skip the synthetic dataset and RAG corpus generation — the entire project's credibility rests on realistic UAE-style data (DHA/Daman-style plan structures, ICD-10/CPT codes, AED amounts). At the end of every phase, run the smoke test listed for that phase before moving to the next. Do not leave placeholders — every function must be complete and runnable. Ask no clarifying questions; all business decisions are pre-made in Section 11.

---

## 1. PROBLEM STATEMENT

UAE health insurance fraud, waste and abuse costs the market an estimated **$1B+ annually** in the Middle East region (BADRI Management Consultancy), against a backdrop of the WTW Global Medical Trends Survey forecasting **10.3% medical cost growth in 2026**, with fraud named as a major driver. This isn't hypothetical: Daman's own Medical Audit Unit has publicly disclosed catching claims with falsified symptoms/medical history and billing for tests never performed, and in April 2026 Everest Health Investments partnered with global claims-fraud specialist Mains Lab to bring real-time AI fraud detection to the UAE market for the first time.

At the same time, UAE regulators (DHA, DoH, Central Bank of UAE) are pushing insurers toward **explainable AI** — a black-box fraud score is not enough; a claims adjuster needs to know *why* a claim was flagged, with a defensible, auditable reason, because a wrongful denial is itself a regulatory and reputational risk.

**The gap:** most fraud-detection tooling in this space (rule engines, black-box ML scorers) can flag a claim but cannot *explain* a decision in terms a human adjuster, auditor, or regulator will accept. ClaimGuard AI closes that gap with a multi-agent pipeline where every recommendation is grounded in — and cites — the actual policy clause that justifies it.

**Target user:** a claims adjuster or TPA (Third-Party Administrator) analyst at a UAE health insurer, triaging a queue of incoming claims.

**Core value proposition:** *"Every decision ClaimGuard makes shows its work — the claim fact, the policy clause it's grounded in, and the reasoning chain — so an adjuster can approve, override, or escalate in seconds instead of minutes."*

---

## 2. SOLUTION OVERVIEW

ClaimGuard AI is a 5-agent pipeline orchestrated with LangGraph:

```
Claim Submitted
      │
      ▼
[1] Intake Agent  ──► extracts structured claim data from raw document
      │
      ▼
[2] Coding Agent  ──► validates ICD-10/CPT code pairs, flags upcoding/unbundling
      │
      ▼
[3] Fraud Scoring Agent ──► XGBoost risk score + top contributing features
      │
      ▼
[4] Policy RAG Agent ──► retrieves cited policy clauses, drafts decision + rationale
      │
      ▼
[5] Decision Router ──► auto-approve / auto-deny / escalate to human
      │
      ▼
Audit Log + Adjuster Dashboard
```

Every agent writes its output — and its reasoning — to a shared `ClaimState` object, so the frontend can render a live, step-by-step "decision trace" rather than a single opaque verdict.

---

## 3. TECH STACK (final decisions — do not deviate)

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui | matches UAE job-spec expectations; production-grade portfolio look |
| Backend | FastAPI (Python 3.11) | async-friendly, pairs cleanly with LangGraph |
| Agent orchestration | **LangGraph** | stateful, controllable multi-agent workflows — the exact keyword in 80%+ of Dubai agentic-AI job postings |
| LLM | Claude API — Sonnet for reasoning agents (Coding, Policy RAG, Router), Haiku for extraction (Intake) | cost-controlled, quality where it matters |
| Vector DB | **Qdrant** (Docker, self-hosted) | free, portfolio-friendly, real vector DB experience (also appears in job specs alongside Pinecone/Weaviate/FAISS) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local, free) or `text-embedding-3-small` if API budget allows | no cost dependency for demo |
| Structured DB | PostgreSQL 15 via SQLAlchemy + Alembic | claims, providers, decisions, audit log |
| Fraud model | XGBoost (you already have this skill from CrediShield) | classic, interview-defensible, explainable via SHAP |
| Document parsing | `pdfplumber` for synthetic claim PDFs, `pytesseract` optional for scanned-image demo | |
| Auth | Simple role selector (Adjuster / Admin) — no real auth system needed for a demo | keeps scope sane |
| Observability | Structured JSON logging of every agent step + LangSmith trace (optional) | matches "observability" line in job specs |
| Deployment | Frontend → Vercel, Backend + Postgres + Qdrant → Docker Compose on Railway/Render | live demo link for your portfolio |

---

## 4. MULTI-AGENT ARCHITECTURE — DETAILED SPEC

### 4.1 Shared State Object (Pydantic)

```python
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import date

class ClaimState(BaseModel):
    claim_id: str
    raw_document_path: str

    # Populated by Intake Agent
    patient_id: Optional[str] = None
    provider_id: Optional[str] = None
    icd10_codes: list[str] = []
    cpt_codes: list[str] = []
    billed_amount: Optional[float] = None
    treatment_date: Optional[date] = None
    plan_type: Optional[str] = None  # "Basic" | "Enhanced" | "Thiqa" | "Comprehensive"

    # Populated by Coding Agent
    coding_flags: list[str] = []          # e.g. ["upcoding_suspected", "diagnosis_procedure_mismatch"]
    coding_confidence: Optional[float] = None

    # Populated by Fraud Scoring Agent
    fraud_score: Optional[float] = None   # 0-100
    fraud_top_features: list[dict] = []   # SHAP-style feature contributions

    # Populated by Policy RAG Agent
    retrieved_clauses: list[dict] = []    # [{clause_id, text, source_doc, similarity}]
    decision_recommendation: Optional[Literal["approve", "deny", "escalate"]] = None
    decision_rationale: Optional[str] = None

    # Populated by Decision Router
    final_decision: Optional[Literal["auto_approved", "auto_denied", "escalated"]] = None
    escalation_reason: Optional[str] = None
    agent_trace: list[dict] = []          # append-only log every agent writes to
```

### 4.2 Agent 1 — Intake Agent

**Job:** turn a raw claim document (synthetic PDF/JSON) into a validated `ClaimState`.
**Tools:** `parse_pdf_tool`, `extract_structured_fields_tool` (Claude Haiku call with strict JSON schema output).
**System prompt (use verbatim, adapt only the schema block if you change fields):**

```
You are the Intake Agent for ClaimGuard AI, a UAE health insurance claims system.
Extract the following fields from the claim document text below. Output ONLY valid JSON
matching this schema — no explanation, no markdown fences:

{
  "patient_id": string,
  "provider_id": string,
  "icd10_codes": [string],
  "cpt_codes": [string],
  "billed_amount": number,
  "treatment_date": "YYYY-MM-DD",
  "plan_type": "Basic" | "Enhanced" | "Thiqa" | "Comprehensive"
}

If a field is missing or illegible in the source text, use null for that field and do not guess.

CLAIM DOCUMENT TEXT:
{document_text}
```

**Failure handling:** if JSON parse fails twice, route claim directly to `escalate` with reason `"intake_extraction_failed"`.

### 4.3 Agent 2 — Coding Agent

**Job:** validate that the ICD-10/CPT code pairs are clinically coherent and check for upcoding/unbundling patterns.
**Tools:** `code_pair_lookup_tool` (queries a small reference table of valid diagnosis-procedure pairings you seed), `policy_rag_query_tool` (same Qdrant index, filtered to `doc_type=coding_policy`).

**System prompt:**

```
You are the Coding Agent for ClaimGuard AI. Given a claim's ICD-10 diagnosis codes and
CPT procedure codes, determine:
1. Are the diagnosis and procedure codes clinically coherent together?
2. Does the billed amount look consistent with the procedure code's typical cost band
   (reference: {cpt_cost_bands})?
3. Is there evidence of unbundling (billing separately for procedures normally billed
   as one bundled code)?

Return JSON:
{
  "coding_flags": [string],       // e.g. ["diagnosis_procedure_mismatch", "amount_outlier"]
  "coding_confidence": number     // 0.0-1.0, your confidence in this assessment
}

CLAIM: {claim_json}
REFERENCE CODE PAIRS: {valid_pairs_sample}
```

### 4.4 Agent 3 — Fraud Scoring Agent

**Job:** run the trained XGBoost model (not an LLM call — a deterministic ML step wrapped as a LangGraph node) and attach SHAP-style feature attributions.

**Feature set (engineer these into the training table):**
- `billed_amount_zscore` (vs. that CPT code's historical mean)
- `provider_claim_frequency_30d`
- `patient_claim_frequency_90d`
- `days_since_last_claim_same_provider`
- `is_weekend_treatment_date`
- `provider_flagged_history_count`
- `coding_flags_count` (from Agent 2 output)
- `plan_type_encoded`

**Node logic (pseudocode, not an LLM call):**

```python
def fraud_scoring_node(state: ClaimState) -> ClaimState:
    features = build_feature_vector(state)
    proba = fraud_model.predict_proba([features])[0][1]
    state.fraud_score = round(proba * 100, 1)
    shap_values = explainer(features)
    state.fraud_top_features = top_n_contributors(shap_values, n=3)
    state.agent_trace.append({"agent": "fraud_scoring", "score": state.fraud_score})
    return state
```

### 4.5 Agent 4 — Policy RAG Agent (the core differentiator — build this carefully)

**Job:** retrieve the actual policy clauses that justify a decision, then draft a recommendation that is *grounded in and cites* those clauses — never a bare LLM opinion.

**Retrieval:** query Qdrant with a composed query string: `"{plan_type} plan, procedure {cpt_codes}, diagnosis {icd10_codes}, prior authorization requirement, exclusions"`. Retrieve top-5 chunks, filter by `plan_type` metadata match.

**System prompt:**

```
You are the Policy RAG Agent for ClaimGuard AI. You must ground every recommendation in
the retrieved policy clauses below — do not invent policy rules that are not present in
the retrieved text.

CLAIM SUMMARY: {claim_summary}
CODING FLAGS: {coding_flags}
FRAUD SCORE: {fraud_score}/100

RETRIEVED POLICY CLAUSES:
{retrieved_clauses}

Based ONLY on the retrieved clauses above, output JSON:
{
  "decision_recommendation": "approve" | "deny" | "escalate",
  "decision_rationale": string,      // must explicitly reference clause_id(s) used
  "cited_clause_ids": [string],
  "confidence": number               // 0.0-1.0
}

If the retrieved clauses do not clearly cover this claim, you MUST return "escalate" —
never guess a policy rule that wasn't retrieved.
```

**This is your interview talking point:** explain that this prompt design is a deliberate hallucination guardrail — the agent is instructed to escalate rather than fabricate a policy rule, which is the difference between a toy RAG demo and a production-credible one.

### 4.6 Agent 5 — Decision Router (deterministic, not an LLM call)

```python
def decision_router_node(state: ClaimState) -> ClaimState:
    if state.fraud_score > 75 or state.decision_recommendation == "escalate" \
       or "diagnosis_procedure_mismatch" in state.coding_flags:
        state.final_decision = "escalated"
        state.escalation_reason = build_escalation_reason(state)
    elif state.decision_recommendation == "approve" and state.fraud_score < 40:
        state.final_decision = "auto_approved"
    else:
        state.final_decision = "auto_denied"
    state.agent_trace.append({"agent": "decision_router", "final": state.final_decision})
    return state
```

### 4.7 LangGraph Wiring (skeleton)

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(ClaimState)
graph.add_node("intake", intake_agent_node)
graph.add_node("coding", coding_agent_node)
graph.add_node("fraud_scoring", fraud_scoring_node)
graph.add_node("policy_rag", policy_rag_agent_node)
graph.add_node("decision_router", decision_router_node)

graph.set_entry_point("intake")
graph.add_edge("intake", "coding")
graph.add_edge("coding", "fraud_scoring")
graph.add_edge("fraud_scoring", "policy_rag")
graph.add_edge("policy_rag", "decision_router")
graph.add_edge("decision_router", END)

claim_pipeline = graph.compile()
```

---

## 5. RAG KNOWLEDGE BASE — SYNTHETIC POLICY CORPUS

Build a `policies/` folder of **12-15 synthetic Markdown documents** styled after real DHA Basic Benefit Plan / Daman-style structures (do not copy real policy text verbatim — write original clauses in that style). Cover:

1. `basic_plan_benefits.md` — DHA-style Basic Benefit Plan coverage table
2. `enhanced_plan_benefits.md`
3. `thiqa_plan_benefits.md` (Abu Dhabi nationals-style plan)
4. `prior_authorization_requirements.md` — list of CPT codes requiring pre-auth
5. `exclusions_and_limitations.md`
6. `copayment_bands.md`
7. `maternity_coverage.md`
8. `chronic_disease_management.md`
9. `emergency_services_policy.md`
10. `pharmacy_benefit_policy.md`
11. `fraud_waste_abuse_definitions.md` — definitions of upcoding, unbundling, phantom billing (for the Coding Agent's RAG queries)
12. `claims_submission_sla.md`

**Chunking:** 300-500 token chunks, one clause per chunk where possible, metadata = `{doc_id, clause_id, plan_type, effective_date, category}`.

**Ingestion script outline (`ingest_policies.py`):**

```python
for doc in load_markdown_docs("policies/"):
    chunks = chunk_by_clause(doc, max_tokens=400)
    for chunk in chunks:
        embedding = embed_model.encode(chunk.text)
        qdrant_client.upsert(
            collection_name="claimguard_policies",
            points=[{
                "id": chunk.clause_id,
                "vector": embedding,
                "payload": {
                    "text": chunk.text, "doc_id": doc.id,
                    "plan_type": chunk.plan_type, "category": chunk.category
                }
            }]
        )
```

---

## 6. SYNTHETIC DATASET DESIGN

**⚠️ Ethics note to state explicitly in your README and in interviews:** all data is synthetically generated. No real patient, provider, or claims data is used anywhere in this project — this matters both for PDPL compliance and because it's the responsible way to build a healthcare-adjacent portfolio project.

### `claims.csv` (~400 rows)
| Column | Type | Notes |
|---|---|---|
| claim_id | string | `CLM-00001` format |
| patient_id | string | synthetic, `PAT-xxxx` |
| provider_id | string | synthetic, `PRV-xxx`, ~40 unique providers |
| icd10_codes | string | comma-separated, drawn from a realistic 50-code sample |
| cpt_codes | string | comma-separated, drawn from a realistic 60-code sample |
| billed_amount | float | AED, with realistic distribution per CPT code + injected outliers |
| approved_amount | float | ground truth for eval |
| claim_date | date | spread across 12 months |
| plan_type | categorical | Basic / Enhanced / Thiqa / Comprehensive |
| prior_auth_required | bool | derived from CPT lookup |
| prior_auth_obtained | bool | ~85% true, rest false (creates escalation cases) |
| fraud_label | bool | **ground truth, injected at ~8% rate** for model training/eval only — never shown to the agents |

### `providers.csv` (~40 rows)
`provider_id, specialty, claim_volume_30d_avg, flagged_history_count`

**Fraud injection strategy (important — write this as a documented function, not manual edits):** programmatically inject 3 fraud archetypes into ~8% of rows so the model has real signal to learn:
1. **Amount inflation** — billed_amount 3-5x the CPT code's normal band
2. **Phantom billing pattern** — same provider, same patient, multiple same-day claims for incompatible procedures
3. **Diagnosis-procedure mismatch** — ICD-10 code that doesn't clinically justify the CPT code billed

---

## 7. DATABASE SCHEMA (PostgreSQL DDL)

```sql
CREATE TABLE providers (
    provider_id VARCHAR(10) PRIMARY KEY,
    specialty VARCHAR(100),
    claim_volume_30d_avg INT,
    flagged_history_count INT DEFAULT 0
);

CREATE TABLE claims (
    claim_id VARCHAR(15) PRIMARY KEY,
    patient_id VARCHAR(10) NOT NULL,
    provider_id VARCHAR(10) REFERENCES providers(provider_id),
    icd10_codes TEXT[],
    cpt_codes TEXT[],
    billed_amount NUMERIC(10,2),
    approved_amount NUMERIC(10,2),
    treatment_date DATE,
    plan_type VARCHAR(20),
    prior_auth_required BOOLEAN,
    prior_auth_obtained BOOLEAN,
    fraud_label BOOLEAN,          -- ground truth, hidden from agent pipeline
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE decisions (
    decision_id SERIAL PRIMARY KEY,
    claim_id VARCHAR(15) REFERENCES claims(claim_id),
    coding_flags TEXT[],
    fraud_score NUMERIC(5,2),
    fraud_top_features JSONB,
    retrieved_clauses JSONB,
    decision_recommendation VARCHAR(20),
    decision_rationale TEXT,
    final_decision VARCHAR(20),
    escalation_reason TEXT,
    agent_trace JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE escalations (
    escalation_id SERIAL PRIMARY KEY,
    claim_id VARCHAR(15) REFERENCES claims(claim_id),
    status VARCHAR(20) DEFAULT 'pending',  -- pending | resolved
    adjuster_decision VARCHAR(20),
    adjuster_notes TEXT,
    resolved_at TIMESTAMP
);

CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    claim_id VARCHAR(15),
    event_type VARCHAR(50),
    event_payload JSONB,
    timestamp TIMESTAMP DEFAULT now()
);
```

---

## 8. API CONTRACTS (FastAPI)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/claims/submit` | ingest new claim document, triggers pipeline |
| GET | `/claims` | list/filter claims queue |
| GET | `/claims/{claim_id}` | claim detail |
| GET | `/claims/{claim_id}/decision-trace` | full agent-by-agent trace for the trace panel |
| GET | `/escalations` | pending escalation queue |
| POST | `/escalations/{id}/resolve` | adjuster resolves an escalated claim |
| GET | `/analytics/fraud-trends` | aggregated stats for dashboard charts |
| WS | `/ws/claims/{claim_id}/stream` | live-stream agent reasoning steps as they run |

---

## 9. FRONTEND / UI SPEC

**Design language:** clinical-trust aesthetic. Not a generic gray SaaS dashboard — calm teal/blue palette, generous whitespace, every AI decision shown *with its reasoning inline*, never as a bare verdict. (When you actually build this, load the frontend-design skill for spacing/typography/component conventions before writing any component.)

**Pages:**
1. **Claims Queue** — table with fraud-score heat coloring, plan type, status chips
2. **Claim Detail** — split view: left = claim facts, right = decision trace timeline (Intake → Coding → Fraud → Policy RAG → Router), each step expandable to show its reasoning
3. **Live Agent Trace Panel** — WebSocket-driven, shows agents "thinking" step by step as a new claim is submitted (this is your best demo moment — build it well)
4. **Escalation Queue** — adjuster working view, approve/deny/override with notes
5. **Analytics** — fraud trend charts (Recharts), coding-flag frequency, escalation rate over time

**The one non-negotiable UI element:** every claim decision card must show the **cited policy clause** inline, not hidden behind a click — this is the feature that makes the "explainability" pitch land visually, not just verbally.

---

## 10. BUILD PHASES (follow in order; run the smoke test before advancing)

| Phase | Deliverable | Smoke test |
|---|---|---|
| 0 | Repo scaffold, Docker Compose (Postgres + Qdrant), `.env.example` | `docker compose up` succeeds, both services healthy |
| 1 | Synthetic dataset generator script (`generate_dataset.py`) | `claims.csv`, `providers.csv` produced with correct row counts and injected fraud archetypes |
| 2 | DB schema + seed loader | tables created, seed data loaded, row counts match CSVs |
| 3 | Policy corpus (12-15 docs) + ingestion script | Qdrant collection populated, spot-check a similarity query returns sensible clauses |
| 4 | XGBoost fraud model training script + eval | model saved, precision/recall/AUC printed and >0.75 AUC on held-out set |
| 5 | LangGraph pipeline (5 agents wired) | run pipeline on 5 sample claims end-to-end, inspect `agent_trace` output |
| 6 | FastAPI endpoints wrapping the pipeline | all endpoints in Section 8 respond correctly via `curl`/Postman |
| 7 | Next.js frontend (all 5 pages) | full flow: submit claim → watch live trace → see it land in queue or escalation |
| 8 | Evaluation harness | metrics report generated (Section 12) |
| 9 | Polish: README, demo seed data, deploy | live URL works, README has setup + architecture diagram |

---

## 11. BUSINESS DECISIONS (pre-made — do not ask, just build)

- **LLM provider:** Claude API (Sonnet for Coding/Policy RAG/Router reasoning calls, Haiku for Intake extraction) — cost-controlled, quality where it counts.
- **Vector DB:** Qdrant, self-hosted via Docker — free, and "I ran my own vector DB" is a stronger interview line than "I used a managed API."
- **Auth:** simple role selector (Adjuster/Admin), no real auth system — keep scope on the agentic/RAG core, not infra.
- **Dataset scale:** ~400 claims, ~40 providers — enough for meaningful fraud patterns without bloating build time.
- **Deployment:** Vercel (frontend) + Railway or Render (backend + Postgres + Qdrant via Docker) — you need a live link, not just a GitHub repo, for recruiters to click.
- **Language scope for v1:** English only. Arabic RAG support is an explicitly named future improvement (Section 14), not v1 scope — don't let this expand the build.

---

## 12. EVALUATION METRICS

- **Fraud model:** Precision, Recall, F1, AUC-ROC on held-out synthetic test set (target AUC > 0.80)
- **RAG retrieval quality:** Retrieval Precision@5 — manually spot-check 20 claims: does the top retrieved clause actually support the decision made?
- **Citation accuracy:** % of `decision_rationale` outputs that correctly reference a `clause_id` that was actually retrieved (should be 100% — enforce via output validation, reject and retry if not)
- **Pipeline latency:** end-to-end time per claim (target < 15s for demo responsiveness)
- **Escalation rate:** % of claims routed to human review — track this as a business KPI, not just a technical one (too high = pipeline isn't confident enough; too low = risk of missed fraud)

---

## 13. LIMITATIONS & ETHICAL CONSIDERATIONS

- All data is synthetic — this is a portfolio demonstration of an architecture pattern, not a validated production fraud system. State this explicitly in the README and in interviews.
- Fraud-scoring ML models can encode and amplify bias if trained on skewed historical data; a production version would need a fairness audit (by provider specialty, patient demographics) before deployment — worth naming unprompted, it shows maturity.
- LLM-cited clauses reduce hallucination risk but are not a legal guarantee of policy compliance; a real deployment would need human sign-off on every auto-decision during a pilot phase, not just escalated ones.
- No real PHI (Protected Health Information) is used anywhere, in line with UAE PDPL principles.

---

## 14. FUTURE IMPROVEMENTS

- Arabic-language claims intake and bilingual policy RAG (matches the UAE's 60%+ Arabic-speaking market segment)
- Computer-vision agent for detecting AI-manipulated damage/document photos (an emerging 2026 fraud vector)
- Real integration with a TPA/insurer sandbox API instead of synthetic documents
- Provider network graph analysis to catch organized fraud rings (multi-claim, multi-provider collusion patterns)
- A/B testing framework to measure adjuster override rate over time as a trust signal

---

## 15. VIVA / INTERVIEW Q&A

**Q1: Why LangGraph instead of CrewAI or a simple chain?**
Because the pipeline needs controllable, inspectable state at every step — an adjuster needs to see exactly what each agent did, not just the final answer. LangGraph's explicit state graph makes that trace a first-class citizen instead of something you have to bolt on.

**Q2: How do you stop the Policy RAG Agent from hallucinating a policy rule?**
Two guardrails: (1) the system prompt explicitly instructs the agent to escalate rather than invent a rule when retrieval is weak, and (2) I validate that every `clause_id` cited in the rationale actually appears in the retrieved set — if not, the output is rejected and retried.

**Q3: Why XGBoost for fraud scoring instead of having the LLM score fraud directly?**
LLMs are good at reasoning over retrieved text, not at learning statistical patterns across thousands of historical claims. XGBoost gives calibrated, auditable probability scores with SHAP explainability — the right tool for a tabular anomaly-detection problem. The LLM's job is to *reason about* that score, not replace it.

**Q4: How is this different from your CrediShield project?**
CrediShield used ANN/CNN/LSTM for credit default, forgery, and transaction fraud in a lending context — pure ML pipelines. ClaimGuard is agentic: it orchestrates multiple reasoning steps, retrieves and cites actual policy documents, and produces a human-readable decision trace. The skill being demonstrated is different — agent orchestration and grounded explainability, not just model training.

**Q5: What happens when the fraud score and the Policy RAG recommendation disagree?**
The Decision Router treats fraud score above threshold as an automatic escalation trigger regardless of what the Policy RAG Agent recommends — a high fraud score always earns a human look, by design. That's a deliberate conservative-by-default choice for a regulated domain.

**Q6: How would this scale to real DHA/Daman data?**
The architecture doesn't change — you'd swap the synthetic policy corpus for licensed real policy documents (with proper data agreements), retrain the fraud model on real historical claims, and add a compliance review step before any auto-decision goes live, likely running in shadow mode against human adjusters for a pilot period first.

**Q7: Why Qdrant over Pinecone?**
Self-hosted, free, and it demonstrates I can run and manage vector infrastructure myself rather than only calling a managed API — a stronger signal for an engineering-adjacent role, and it removes a recurring cost from a portfolio project.

**Q8: What's the biggest limitation of this system as built?**
It's trained and evaluated entirely on synthetic data, so its fraud-detection accuracy numbers don't generalize to real claim patterns — the value of the project is the architecture and the explainability pattern, not the specific model weights.

**Q9: How do you measure whether the RAG retrieval is actually good, not just plausible-looking?**
Retrieval Precision@5 via manual spot-check against a labeled sample, plus enforcing that every cited clause_id must actually be in the retrieved set — that second check is a stronger signal than eyeballing outputs because it's a hard, checkable constraint.

**Q10: Why did you build this project specifically, given the UAE market?**
The UAE has a well-documented health insurance fraud problem (Daman's own fraud disclosures, the Everest Health/Mains Lab partnership announced this year) and a regulatory environment that's explicitly pushing insurers toward explainable AI, not black-box scoring. This project is a direct, defensible answer to a named, current market gap — not a generic chatbot demo.

---

## 16. RESUME / LINKEDIN POSITIONING

**Resume bullet options:**
- *Built ClaimGuard AI, a 5-agent LangGraph pipeline for health insurance claims triage that grounds every fraud/coverage decision in cited policy clauses via a self-hosted Qdrant RAG pipeline, reducing black-box risk in a regulated domain.*
- *Designed and trained an XGBoost fraud-scoring model (AUC 0.8+) integrated into a multi-agent decision pipeline with automatic escalation routing and full audit-trail logging.*
- *Engineered a hallucination-guardrailed RAG agent that enforces citation validation on every LLM-generated policy recommendation.*

**30-second elevator pitch:**
*"UAE health insurers lose over a billion dollars a year to claims fraud, and regulators are pushing them toward explainable AI instead of black-box scoring. I built ClaimGuard AI — a five-agent system that triages claims, scores fraud risk, and then grounds its recommendation in the actual policy clause it's based on, so an adjuster sees the reasoning, not just a verdict. It's built on LangGraph and a self-hosted Qdrant RAG pipeline, and it's the same explainability pattern regulated industries like banking and insurance are actively hiring for right now."*

---

## 17. SUBMISSION CHECKLIST

- [x] Repo scaffold + Docker Compose running
- [x] `generate_dataset.py` produces `claims.csv` + `providers.csv` with documented fraud injection
- [x] 12-15 synthetic policy documents in `policies/`, ingested into Qdrant
- [x] XGBoost model trained, eval report saved
- [x] LangGraph pipeline runs end-to-end on sample claims, full `agent_trace` visible
- [x] All 8 API endpoints functional
- [x] Next.js frontend: Queue, Claim Detail, Live Trace Panel, Escalation Queue, Analytics
- [x] README with architecture diagram, setup instructions, ethics/limitations section
- [ ] Live deployed URL (see README — local demo verified end-to-end in this build environment; see README "Deploying it live" for the Vercel/Railway steps to get a public link)
- [x] This master prompt doc included in repo as `ARCHITECTURE.md`

> **Note on implementation deviations, added for transparency (not part of the original prompt):** see `README.md` → "Notes on faithfulness to this spec" for the handful of pragmatic substitutions made to run fully offline in the build sandbox (SQLite/Postgres both supported, embedded Qdrant by default, an embedding fallback when Hugging Face is unreachable, and a documented Next.js version pin).
