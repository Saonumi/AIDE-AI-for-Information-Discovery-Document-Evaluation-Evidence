---
checkpoint: 1 (Idea Evaluation)
competition: Vietnam AI Innovation Challenge 2026 (VAIC 2026)
problem: SHB1 — Advanced RAG Knowledge Base – AI Chatbot for Complex Banking Document Retrieval
project_name: RegVault
one_liner_en: Verified regulatory knowledge & AI compliance review platform for Vietnamese banks
one_liner_vi: RegVault – Nền tảng kho quy định đã xác minh & kiểm tra tuân thủ bằng AI cho ngân hàng Việt Nam
sections: [project_name_description, product_concept_3_levels, target_customer_persona, project_evaluation_5_criteria]
evaluation_criteria: [innovation, feasibility, big_impact, market_size, scale_up_ability]
status_evidence: 97 tests passing · live head-to-head benchmark vs Standard RAG · real SBV corpus (40+ documents, 30 mined amendment relations)
---

# Check-point 1 — Idea Evaluation

> **RegVault** — *Dự án nền tảng tri thức pháp lý đã xác minh & kiểm tra tuân thủ tài liệu bằng AI cho ngân hàng Việt Nam.*
> (EN: Verified regulatory knowledge & AI-assisted compliance review platform for Vietnamese banks.)

---

## I. Project Name & Description

**Name.** **RegVault** = *Regulation* + *Vault*. A vault holds only what has been verified and lets you prove, at any time, what was inside on any given date. That is precisely the product's trust model: **no document becomes legal ground truth just because it was uploaded** — only sources that are `AUTHORITY_SOURCE + APPROVED + ACTIVE` and *valid at the query date* may serve as legal evidence.

**Description (2 sentences).** RegVault helps a bank's Legal & Compliance officers build a **verified repository of regulations** (parsed to Điều/Khoản/Điểm, versioned over time, every change human-reviewed), and then uses that same repository to **automatically assess the impact of new regulations** and **check internal policies/reports for compliance** — every conclusion carries a version, an effective date, evidence spans, and a human-review status.

**Origin of the problem (SHB1 problem statement).** SHB manages thousands of internal and external regulatory documents (SBV, Government, Basel…). One regulation may be amended many times; individual clauses can be partially superseded. Conventional RAG systems cannot model these relationships and confidently answer from **outdated versions** — a real compliance risk. This remains difficult even for leading global financial institutions.

**Positioning sentence.** *One flow verifies regulations before they enter the knowledge vault; a second flow uses that verified vault to review policies and reports — AI proposes, the Compliance Officer decides.*

---

## II. Product Concept (3 Levels of Product)

### Level 1 — Core Customer Value
**Compliance conclusions the bank can trust and defend.** The right provision, the right **version at the right point in time**, with verifiable evidence — reducing legal & compliance risk and freeing **2–3 hours/day per compliance officer** (benefit stated in SHB's own problem statement). The core value is not "answers"; it is **auditable certainty**.

### Level 2 — Actual Product
- **Quality level.** Deterministic temporal engine: version validity, amendment patching, conflict flags and citations are decided by **deterministic code + graph, never by the LLM**. Verified by **97 automated tests** and an in-product benchmark: on LLM-independent metrics our system scores **100% point-in-time accuracy vs 75%** for Standard RAG, **100% vs 0% cross-reference recall**, **100% vs 0% stale-policy detection**, and **half the superseded-evidence rate (26% vs 53%)** on the 22-question golden set.
- **Features.**
  - **Workflow A — Add Regulatory Source:** upload → injection scan & quarantine → parse Chương/Điều/Khoản/Điểm → review package → **Human Review of every change** → activation hard gate (HTTP 409 until critical reviews clear) → deterministic versioning `[valid_from, valid_to_exclusive)` + reified ChangeEvent → **Regulatory Impact Report** (which internal policies are now affected).
  - **Workflow B — Check Document Compliance:** upload a policy/report as `REVIEW_TARGET` (never enters the legal vault) → claim extraction (amounts, %, deadlines, references) → comparison against the **approved vault as of the review date** → 7 assessment statuses (COMPLIANT, NON_COMPLIANT, PARTIALLY_COMPLIANT, OUTDATED_REFERENCE, MISSING_EVIDENCE, AMBIGUOUS, NEEDS_HUMAN_REVIEW).
  - **"Why this answer" panel:** every answer shows the evidence used **and the sources excluded, with reasons** (NOT_VALID_AT_QUERY_DATE / SUPERSEDED / NOT_APPROVED).
  - **Head-to-head button:** Standard RAG answers incorrectly *live* next to our correct, cited answer — the benchmark is a product feature, not a slide.
  - **Compliance-Gap Radar:** when a regulation changes, the system flags which internal policies are now **STALE**.
  - **Vietnamese legal normalizer:** "500 triệu" ↔ "500.000.000" ↔ "0,5 tỷ" ↔ Vietnamese date formats — without it, patch/conflict/compliance comparisons silently fail.
  - Knowledge-graph visualization, clause version timeline, review inbox, audit log, JWT/RBAC.
- **Design & packaging.** FastAPI + Streamlit web app on PostgreSQL (source of truth) + OpenSearch (BM25 + vector, RRF) + Neo4j (temporal regulatory graph) + bge-m3 embeddings; ships as Docker Compose; runs fully **offline in demo mode** (in-memory fallbacks) — deployable inside a bank's own network so documents never leave.
- **Brand.** RegVault — "the vault your auditors can open."

### Level 3 — Augmented Product
- **Human-Review workflow built in** (review inbox, approve/edit/reject, before/after diffs) — the human-in-the-loop is a product feature, not an afterthought.
- **Full audit trail** (who, when, which evidence, which decision) — usable in front of internal audit and SBV inspectors.
- **Live data feed:** robots-aware crawler for SBV/VBPL official sources (40+ real NHNN documents, 30 real amendment relations already mined) keeps the vault current.
- **Evidence-linked reports:** Regulatory Impact Report & Compliance Review Report with severity and suggested fixes (JSON contract ready; DOCX/PDF export on roadmap).
- **Deployment & support:** on-premise or private-cloud install, onboarding of the bank's golden domain, acceptance testing with our benchmark harness (`eval/`), security review pack (prompt-injection defenses, RBAC, citation allowlist).
- **Warranty of honesty:** the system **abstains** (MISSING_EVIDENCE) instead of guessing, and demo data provenance is labeled — honesty about limits is itself a compliance feature.

---

## III. Target Customer (B2B) — Customer Persona

> **Segment:** Legal & Compliance departments of Vietnamese credit institutions (49 banks; first design partner profile: mid-to-large joint-stock commercial bank like SHB). **User** = compliance officer; **buyer** = Head of Legal & Compliance / CCO; **veto holders** = CTO/CISO (security), Finance (budget).

**Persona — "Ms. Thu Hà", Head of Legal & Compliance, joint-stock commercial bank (HQ Hà Nội)**
- **Profile:** Female, 41, Master of Banking Law; 15 years in banking; leads a team of ~25 legal/compliance officers; income ~70 triệu VND/month; married, 2 children.
- **A day at work:** scans new SBV/Government documents every morning; assigns officers to trace which internal policies are affected; signs off compliance opinions; prepares for SBV thematic inspections; answers "is this report still citing the current regulation?" dozens of times a week.
- **Channels / influence factors:** SBV portal & VBPL, thuvienphapluat/LuatVietnam, professional email & Zalo groups of bank legal officers, Vietnam Banks Association seminars, Big-4 advisory notes, peers at other banks, findings from previous SBV inspections.
- **Hopes & dreams:** zero findings in the next SBV inspection; a team that spends time on judgment, not manual cross-checking; being seen by the Board as the department that *enables* fast product launches safely.
- **Worries & fears:**
  - A report cites **500 triệu** where the amended regulation now says **700 triệu** — and the inspector finds it first.
  - An amendment silently changes 5 articles across 3 documents and one internal policy is missed.
  - A conclusion like "policy X is still compliant" with **no evidence trail** of which clause, which version, which page.
  - Generic AI chatbots that answer fluently from **expired versions** or hallucinate citations — and the fear that bank documents leak to external AI services.
  - Personal accountability: her signature is on the compliance opinion.
- **Looking for:** a system that (1) always answers on the correct in-force version, (2) shows evidence *and* what was excluded and why, (3) keeps the final decision with her team, (4) can be deployed inside the bank.
- **Finance:** has an annual budget line for legal databases & compliance tools; willing to pay when risk reduction is demonstrable (one avoided violation or one inspection finding outweighs the license fee).
- **Make her life easier:**
  - New circular lands → **automatic impact report**: which internal policies are now stale, with before/after and effective dates.
  - Draft policy/report → **one-click compliance check** with claim-level statuses and suggested corrections.
  - Every conclusion → an **evidence package she can defend** in front of auditors and inspectors.

---

## IV. Project Evaluation (5 Criteria)

### 1. INNOVATION — what is new vs. what exists today?

| Existing option | What it does well | Why it fails Ms. Hà |
|---|---|---|
| Legal databases (thuvienphapluat, LuatVietnam) | Coverage, consolidated texts | Search only — she still reads, cross-references and assesses impact manually |
| Generic LLM chatbots / standard RAG | Fluent answers | **Version-blind**: mixes superseded and current text; unverifiable citations; no audit trail |
| Global GRC suites (Thomson Reuters, Wolters Kluwer…) | Mature workflows | Expensive, not native to Vietnamese legal structure (Điều/Khoản/Điểm), no Vietnamese normalizer, cloud-only |
| **RegVault** | **Point-in-time correctness + verifiable evidence + human-in-the-loop, Vietnamese-native** | — |

**Technology innovations (Industry 4.0 mapping: AI · Big Data & Analytics · Knowledge Graph · Cloud · Cybersecurity · Everything-as-a-Service):**
1. **Temporal Knowledge Graph with reified ChangeEvents** — amendments are first-class nodes with evidence, operation, before/after versions and effective dates, not just "SUPERSEDES" edges.
2. **Temporal pre-filter *before* top-k retrieval** — the classic silent failure of RAG on versioned corpora (filtering after top-k can never surface the historical version) is designed out.
3. **Deterministic partial patching** — amendments are applied by exact-match rules (REPLACE/INSERT/DELETE/REPEAL); 0 or >1 matches force human review. The LLM never rewrites legal text.
4. **"Caged LLM" architecture** — the LLM cannot choose versions, apply amendments, create citations, decide conflicts, or generate graph queries. It only extracts (with evidence spans) and explains over a pre-assembled, filtered evidence package. A citation verifier rejects any citation outside the evidence allowlist.
5. **Verifiable Evidence Trace** — answers ship with used *and excluded* sources + exclusion reasons; an auditor can replay the decision.
6. **Vietnamese legal number/date normalization** — the unglamorous piece that makes patching and conflict detection actually work on Vietnamese text; most teams skip it.
7. **Benchmark-in-product** — a `/compare` endpoint runs Standard RAG side-by-side, so the innovation is demonstrable live, not claimed.

### 2. FEASIBILITY — USPs + resources; why this can actually be built (it already is)

**Proof of feasibility (working MVP today):**
- **97 automated tests passing**; full pipeline runs offline (`DEMO_MODE=true`, no Docker, no API keys) and in full 4-store deployment (PostgreSQL + OpenSearch + Neo4j + LLM) via `docker compose up`.
- **Real data:** robots-aware crawler for SBV/VBPL; 40+ real NHNN documents; 30 real amendment relations mined from official sources; 3 named real amendment pairs (e.g., 08/2026/TT-NHNN→22/2019: short-term capital ratio 34%→30%).
- **Live 10-scene demo** including the activation gate refusing un-reviewed sources with HTTP 409 — a business rule at the service layer, not UI decoration.

**USP (winning zone):** *What customers want* (trustworthy, current-version, auditable answers) ∩ *what we do uniquely well* (deterministic temporal engine + evidence trace + HITL) — competitors sit outside this intersection: legal DBs have coverage but no automation; generic AI has fluency but no trust. 
**USP statement:** **"Every answer is point-in-time correct and auditable — AI proposes, the Compliance Officer decides."**

**Business Model Canvas (condensed):**
- **Key partners:** SBV/VBPL open legal data; SHB as design partner; LLM providers (Anthropic/OpenRouter — swappable); university mentors; on-prem infra vendors.
- **Key activities:** golden-domain corpus onboarding; parser/normalizer upkeep; model-agnostic LLM integration; security hardening; customer success with compliance teams.
- **Key resources:** temporal graph engine + deterministic patch engine (the moat); eval harness with golden questions; SBV crawler; codebase with 97-test safety net.
- **Value proposition:** auditable, point-in-time-correct compliance answers and reports; 2–3 h/day saved per officer; inspection-ready evidence trails.
- **Customer relationships:** pilot (1 golden domain) → annual license + SLA support → expansion to more domains/departments.
- **Channels:** direct B2B sales to bank Legal & Compliance; Vietnam Banks Association; VAIC/SHB showcase; Big-4 advisory referrals.
- **Customer segments:** Vietnamese credit institutions (start: joint-stock commercial banks); later securities, insurance, other regulated industries.
- **Cost structure:** engineering team; LLM API usage (capped — LLM is only used for extraction/explanation); infra; enterprise sales cycle.
- **Revenue streams:** annual platform license per institution; implementation/onboarding fee; usage-based document-review packs; (future) per-domain modules.

### 3. BIG IMPACT — what does it fix for the economy & society?

- **Financial-system safety (economic).** Compliance failures at banks propagate to the whole economy. RegVault attacks the root cause SHB named: decisions made on outdated regulations. Fewer violations → fewer fines, safer credit operations, smoother SBV supervision.
- **Productivity (economic).** SHB's own estimate: **2–3 hours/day saved per compliance officer**. For a mid-size bank (~30 officers), that is ≈ **19,000 officer-hours/year** (~2.8 tỷ VND/year of expert time at 150k VND/h) redirected from manual cross-checking to actual judgment — per bank.
- **Responsible-AI governance model (social).** "AI proposes, human decides" with evidence and audit trails is a **transferable template** for applying AI in any high-stakes Vietnamese public domain (tax, customs, healthcare regulation) — directly aligned with Vietnam's national digital-transformation agenda.
- **Knowledge sustainability (organizational).** Regulatory knowledge stops living in senior officers' heads: versions, changes and rationales are preserved — faster onboarding, resilience to staff turnover, standardized organizational knowledge (a benefit SHB explicitly requested).
- **Governance = the "G" in ESG.** An auditable decision trail for every compliance conclusion strengthens corporate governance ratings and inspection readiness.

### 4. MARKET SIZE — PAM → TAM → SAM → SOM

*(Method mirrors the taught PAM/TAM/SAM/SOM framework; assumptions stated explicitly.)*

- **PAM — Potential Addressable Market.** Everyone worldwide who must keep operations aligned with changing regulation: the **global RegTech market ≈ US$22.3B in 2026 → US$85.5B by 2035 (CAGR 16.1%)**, with **Asia-Pacific the fastest-growing region (~18.5% CAGR)** (Precedence Research, 2026).
- **TAM — Total Addressable Market (Vietnam financial sector).** ~**225 regulated financial institutions**: 49 banks (bankervn, 07/2026) + ~16 finance companies + ~80 securities firms + ~80 insurers. Formula: (49 banks × 2 tỷ VND/yr) + (~176 NBFIs × 0.5 tỷ VND/yr) ≈ **~190 tỷ VND/year (~US$7.5M ARR)** for regulatory-knowledge software licenses.
- **SAM — Serviceable Available Market.** Institutions our direct B2B channel can reach in VN: **35 domestic commercial banks + 16 finance companies ≈ 51 institutions** × avg 1.5 tỷ VND/yr ≈ **~75 tỷ VND/year (~US$3M)**.
- **SOM — Serviceable & Obtainable Market (3 years).** **SHB pilot + 9 more institutions = 10 customers (~20% of SAM)** × 1.5 tỷ VND ≈ **~15 tỷ VND/year ARR (~US$600K)**.
- **Value check (why 1.5 tỷ/yr is buyable):** time savings alone ≈ 2.8 tỷ VND/yr per mid-size bank (calc above) → **~1.9× ROI before counting a single avoided fine or inspection finding.**

### 5. SCALE-UP ABILITY

**Product scales by adding data, not code.** Index separation (authority / internal-policy / review-workspace), outbox sync, PostgreSQL as source of truth: onboarding a new domain or a new bank = new documents through Workflow A, not new engineering. Per-bank on-prem images or multi-tenant SaaS from the same codebase.

**Expansion waves:**
1. **2026 — SHB pilot:** one golden domain (credit) deep, inspection-ready.
2. **2027 — Vietnamese banking:** 10 institutions; add domains (FX, AML, capital adequacy); DOCX/PDF report export; OCR for scanned archives.
3. **2028 — regulated verticals VN:** securities, insurance, pharma, energy — same engine, new corpora; usage-based document-review API pricing.
4. **2029+ — ASEAN:** the architecture is language-agnostic; localization = swapping the normalizer + structure-parser patterns (the Vietnamese modules prove the pattern). Target APAC, the fastest-growing RegTech region.

**Operational scale-up (7 core priorities):** Strategy — compliance-first vertical AI, auditability as the moat; Product proposition — "the vault your auditors can open," massive headroom (every regulated industry); People — pair compliance SMEs with AI engineers; hire from bank legal teams; Infrastructure — containerized, storage-agnostic, LLM-provider-agnostic; Execution — repeatable pilot→license playbook (golden domain in <6 weeks using our crawler + review inbox); Finance — license revenue + implementation fees fund expansion; LLM cost is structurally low because the LLM only writes explanations, never does retrieval-scale work.

---

## Honesty box (what we do NOT claim)

- Not a "GraphRAG chatbot" and not a system that issues final legal conclusions — **AI proposes, the Compliance Officer decides**.
- Uploaded files are never auto-added to the knowledge base; conflict/impact outputs are **candidates for human review**.
- Benchmark numbers for generation-dependent metrics were measured with an offline mock LLM (lower bound); LLM-independent metrics (point-in-time, cross-reference, stale-policy, abstention) are decided by deterministic code and hold regardless of LLM.
- Current limits: OCR for old-font scanned PDFs not yet enabled; purely semantic claims route to NEEDS_HUMAN_REVIEW; DOCX/PDF export is roadmap.

## Sources
- SHB1 Problem Statement, VAIC 2026 (benefits: current regulations, 2–3 h/day saved, reduced compliance risk).
- Precedence Research — RegTech Market (2026 ≈ US$22.3B; 2035 ≈ US$85.5B; CAGR 16.1%; APAC ~18.5%): precedenceresearch.com/regtech-market
- Bank count Vietnam (49, as of 03/07/2026): bankervn.com/danh-sach-ngan-hang
- Internal evidence: `docs/PITCH.md`, `docs/project.md` §10 (benchmark, 9/9 deterministic checks), test suite (97 passed), `eval/run_eval.py` golden set.
- Assumptions (marked): license pricing 0.5–2 tỷ VND/yr; 30 officers/bank; 150k VND/h expert cost; VND/USD ≈ 25,500.
