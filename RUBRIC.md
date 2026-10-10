# RUBRIC.md — Self-Assessment: HHV Copilot

Scored against `~/workspace/peaii-hackathon/judging-rubric.md`
(100 points, 1–5 scale per criterion). Scores are the builder's honest
self-assessment, with evidence a judge can verify by running `python3 demo.py`
and reading the code.

## Criterion scores

| # | Criterion | Weight | Score | Points | One-line evidence |
|---|-----------|--------|-------|--------|-------------------|
| 1 | Problem Definition & Real-World Impact | 25 | 4/5 | 20 | Specific user (MA plan care/quality teams) + real HHV lifecycle pain: need-based identification, cancel→rebook, 3-source reconciliation |
| 2 | Meaningful Agentic AI Behavior | 20 | 4/5 | 16 | Visible plan, 8 tool calls, multi-step reasoning, prior-cycle memory recalled/applied/stored, replanning on the injected discrepancy |
| 3 | Working Prototype | 15 | 4/5 | 12 | Full 7-step lifecycle runs in <1s, exit 0, byte-identical across 10 runs (TEST-LOG.md); eval harness built in |
| 4 | Innovation & Creativity | 15 | 3/5 | 9 | Classify-before-disposition reconciliation + "absence of evidence ≠ evidence of absence" as coded rules; HHV orchestration itself isn't a novel category |
| 5 | Presentation & Communication | 15 | 4/5 | 12 | Printed plan/trace readable by non-technical audiences; README has timed speaker notes and live-demo cues |
| 6 | Responsible AI & Feasibility | 10 | 5/5 | 10 | Six hard rules enforced in code (see below); decision-support framing; synthetic-data limits stated on screen |
| | **TOTAL** | **100** | | **79** | |

## Evidence, honest gaps, and how a student could close them

### 1. Problem Definition & Real-World Impact — 4/5 (20/25)
**Evidence.** The problem is specific and real: Medicare Advantage plans run in-home assessments through vendors, and the operational failure modes are well known — outreach that chases utilization or revenue instead of need, cancellations that become dead ends, assessments whose findings never reach a PCP, and follow-up records lost across scheduling/vendor/claims systems. The demo names its user (plan care-management/quality teams), shows the "refuse to do" (utilization-only ranking overlaps the need-based cohort at Jaccard 0.16; 8 high utilizers excluded for no care opportunity), and walks one member end to end.
**Honest gap.** All impact is demonstrated on synthetic data; nothing here proves real members would be better served. The payer's real constraints (vendor contracts, STAR-measure economics, staffing) are simplified away.
**How a student could close it.** Interview one care manager or quality nurse; add one real workflow constraint they name (e.g., HEDIS measure deadlines) as a seventh hard rule and show it changing the agent's behavior.

### 2. Meaningful Agentic AI Behavior — 4/5 (16/20)
**Evidence.** The orchestrator prints its plan, then executes: `load_registry → identify_members → schedule_visit → extract_findings → validate_protocols → create_task → reconcile_sources → render_dashboard`, with `[MEMORY]` recall/store operations interleaved. Genuine multi-step reasoning is visible twice: the cancel→investigate-reason→recall-2025-learning→rebook-with-transportation loop, and the discrepancy→4-checks→classify→UNRESOLVED→rerun-on-new-file→human-close loop. Remove the agent and you lose the looping, the memory, and the replanning — a script wouldn't recover from the cancellation or the missing claim.
**Honest gap.** There is no real LLM: the "orchestrator's intelligence" is deterministic Python. The agentic *pattern* is real; the model behind it is simulated.
**How a student could close it.** Replace `extract_findings`' rule classifier with an LLM call behind the same function contract, keep the invented-diagnosis guardrail, and show the trace unchanged — proving the architecture survives the swap.

### 3. Working Prototype — 4/5 (12/15)
**Evidence.** `python3 demo.py` runs the complete 7-step sequence in under a second, exits 0, and produces byte-identical output across 10 consecutive runs (TEST-LOG.md, one shared SHA-256). The reconciliation classifier is exercised on 8 labeled cases inside the run itself.
**Honest gap.** No real integrations: EHR feeds, claims systems, and vendor files are simulated dicts. The 8-case eval is hand-labeled by the builder.
**How a student could close it.** Add a second, independently written set of eval cases (a teammate writes them blind), or wire one tool to a real local data file (e.g., a CSV of de-identified public CMS data) instead of in-code dicts.

### 4. Innovation & Creativity — 3/5 (9/15)
**Evidence.** The creative core is treating responsible-AI rules as *architecture*: revenue fields exist in the data and are provably unread (verified by source inspection at runtime); the diagnosis guardrail raises instead of warning; "absence of evidence is not evidence of absence" is a disposition rule, not a slogan; the agent's own task-closing attempt is denied live. Classify-before-disposition as a reconciliation pattern is unusual in demos.
**Honest gap.** HHV orchestration demos exist; the lifecycle framing and guardrail-as-code design are refinements, not a breakthrough category.
**How a student could close it.** Invent one genuinely new interaction: e.g., let the audience inject their own discrepancy at demo time (a `--inject` flag) and watch the classifier handle an unseen case live.

### 5. Presentation & Communication — 4/5 (12/15)
**Evidence.** The trace is narratable by a non-technical presenter: plan, tool calls, memory, guardrails, and the discrepancy story all print in plain language. README includes timed speaker notes (~6–7 min), exact say-lines, and live-demo cues (the guardrail denial, the "what would your boss optimize for?" question).
**Honest gap.** No visuals — no screenshots, no funnel diagram rendered from the actual run.
**How a student could close it.** Capture terminal output into 2–3 annotated screenshots for the README, or render the funnel + task timeline as a simple HTML page from the demo's own data structures.

### 6. Responsible AI & Feasibility — 5/5 (10/10)
**Evidence.** This is the demo's strongest criterion. Six hard rules are *enforced in code*, each demonstrable in the run:
1. **Never invent diagnoses** — `guard_no_invented_diagnoses` raises on banned phrases; dizziness stays "reported, cause undetermined."
2. **Never revenue-optimize** — runtime source inspection proves the identifier never references `est_risk_revenue_usd` / `documented_dx_count`.
3. **Never change meds** — med-rec task constraint; agent medication changes: 0.
4. **Human-only task completion** — `transition_task` raises `PermissionError` for the agent; the denial is shown live; both completed tasks were closed by named humans (Dana Whitfield, Sam Reyes).
5. **Classify before disposition** — the reconciler cannot disposition without a classification; UNRESOLVED is a first-class state, not a failure.
6. **No outcome claims** — the dashboard explicitly states visits ≠ health outcomes.
Plus: synthetic-data banner on screen, decision-support (not denial-of-care) framing, and honest limits printed at the end.
**Honest gap.** Code guardrails are necessary but not sufficient for real deployment: clinical validation, privacy/security review, and bias auditing on real data are all still required — the demo says so on screen.
**How a student could close it.** Run a bias audit: stratify identification rates by zip/age/sex in the synthetic registry and add the disparity table to the dashboard — then discuss what it would mean on real data.

## The five evaluation dimensions (computed by the demo)

| Dimension | Result | Evidence in the run |
|---|---|---|
| Prioritization agreement | precision 99.6% (264/265), recall 31.6% | Agent's 265 picks vs an independently written care-manager checklist (836 flagged as a broad net): nearly every pick is checklist-flagged; the agent prioritizes rather than screening broadly |
| Extraction accuracy | 10/10, 0 invented diagnoses | 10 findings classified reported/verified/care_gap on the scripted assessment; guardrail count printed |
| Reconciliation precision / recall | 1.00 / 1.00 | 8/8 hand-labeled cases correct: processing delay, missing-past-lag, ID mismatch, date inconsistency, incomplete file, duplicate files, full agreement, source conflict |
| Routing correctness | 3/3, 0 agent med changes | PCP follow-up → Care Coordinator; med rec → Clinical Pharmacist; transportation → Transportation Coordinator |
| Workflow reliability | 10/10 byte-identical | TEST-LOG.md: 10 consecutive runs, exit 0, one shared SHA-256 |

**Reading these honestly:** dimensions 2–4 are validated on small, builder-authored fixtures — they prove the *plumbing* (classification, routing, guardrails) works, not that a production model would. Dimension 1's precision/recall split is the most instructive: high precision says the agent's definition of need matches a clinician's; low recall is *by design* (capacity-limited outreach). A student extending this should grow the eval sets before claiming more.

## What the six judge questions get as answers

1. **What problem?** HHV programs fail operationally: wrong members targeted, cancellations wasted, findings never acted on, follow-ups lost across systems.
2. **Who?** Medicare Advantage plan care-management and quality teams (not "everyone").
3. **Why does it matter?** Every unresolved care gap is a missed intervention; every mis-targeted visit is wasted clinical capacity.
4. **Why AI?** The loop — investigate a cancellation's reason, recall what worked last cycle, rebook smarter; investigate a discrepancy across three systems instead of assuming — is judgment-heavy work that rules alone do badly.
5. **Why an *agent*?** Planning (printed plan), tool use (8 tools), multi-step reasoning (two recovery loops), memory (prior-cycle learnings) — remove any one and the demo's centerpiece scenes collapse.
6. **Does it work?** Run `python3 demo.py`: 7 steps, <1s, exit 0, byte-identical 10/10.
