# HHV Copilot — An Agentic AI System for Medicare Advantage In-Home Assessments

**Demo 5 of 5 · Agentic AI Workshop**

> **Educational demo.** All 1,000 members are synthetic (generated in-code,
> fixed seed). Clinical details are fictional teaching examples, not medical
> advice. No network, no API keys, no costs.

---

## Open in Chrome (live web UI)

Every demo is demoable live in Google Chrome via a localhost web app —
stdlib only, nothing to install.

```bash
cd ~/workspace/agentic-ai-workshop/hhv-copilot
python3 app.py
```

Then open **http://localhost:8002** in Chrome and press **▶ Run live
demo**. The page runs `python3 demo.py` on your machine and renders the
agent's plan, tool calls, and results in styled panels. (Binds
127.0.0.1:8002; if the port is already in use, `app.py` says so plainly.)

---

## Real-world problem, target users, market need, and differentiation

**The problem.** A health plan can't send a clinician to every member, so
it runs in-home health assessment (HHV) visits for a targeted cohort. The
hard parts aren't the model: they're everything around it — picking
members for the right reasons, handling cancellations, interpreting
assessments without inventing diagnoses, closing care gaps through humans,
reconciling messy data across systems, and reporting honestly.

**Target users.** Medicare Advantage plan operators — program managers,
care coordinators, and vendor-operations teams running HHV programs at
scale.

**Market need.** Every stage of the HHV lifecycle is a place where naive
automation fails dangerously: prioritizing by revenue instead of need,
closing tasks on missing data, inventing diagnoses from ambiguous notes,
claiming health outcomes from operational dashboards. The need is an agent
that runs the full lifecycle with hard rules enforced in code — and knows
where humans must decide.

**Differentiation.** This demo runs the **full lifecycle**, not just a
prioritization model: six stages from member identification to program
performance, with deterministic guardrails (the agent provably can't read
revenue fields, can't invent diagnoses, can't close tasks itself). Its
dramatic center is the injected discrepancy: the PCP follow-up record is
**missing from claims**, and instead of closing the task ("2 of 3 sources
say done") or declaring the visit never happened, the agent *investigates*
four checks, classifies it `EXPECTED_PROCESSING_DELAY` (claim is 8 days
old; normal lag is 30–45), marks the task **UNRESOLVED** — not failed —
and re-checks when the updated claims file arrives. Then a human closes it.
Absence of evidence is not evidence of absence.

---

## Meaningful Agentic AI functionality

**Why an agent, not a chatbot?** A chatbot could summarize an assessment.
This system *runs a six-stage program*: one orchestrating agent (**HHV
Copilot**) that prints its plan and calls specialized tools, with
deterministic guardrails around every consequential step:

1. **Member Identification** — 1,000 synthetic members → 265 identified for
   outreach, on need-based criteria. Never high-utilization-only; never
   revenue-optimized (revenue fields provably unread).
2. **Outreach & Scheduling** — cancel → rebook agentic loop: Margaret Ellis
   cancels (no ride) → the agent recalls the 2025-cycle learning, rebooks
   with transportation bundled.
3. **Assessment Interpretation** — 10 findings extracted as **reported** vs
   **verified** vs **care gap**; protocol validation; clinician-review
   flags. NEVER invents diagnoses (guardrail raises on violation).
4. **Care Gap Resolution** — 3 tasks (PCP follow-up, medication
   reconciliation, transportation) tracked to completion. The agent NEVER
   changes meds; ONLY authorized humans complete tasks (the denial is
   demonstrated live).
5. **Data Validation & Reconciliation** — 3-source discrepancy (scheduling
   ✓ / vendor ✓ / claims ✗) → investigate → classify **before** disposition.
6. **Program Performance** — operational dashboard: funnel, task rollup,
   bottlenecks. NEVER claims health outcomes improved.

The orchestrator/tool split is the whole lesson: `extract_findings` could
become an LLM call and `CopilotMemory` a vector store in a real build — the
contracts (and the guardrails around them) stay the same. Students see
*where* the AI goes and *where* deterministic rules must hold.

---

## Project scope, inputs, outputs, constraints, success criteria, and definition of done

**Scope.** A deterministic, offline run of the full 7-step HHV lifecycle
(charter → 6 stages → dashboard + self-eval), deep-diving on featured
member HHV-M0042 (Margaret Ellis, 78), in 6–7 minutes, exiting 0.

**Inputs (all synthetic).**

- 1,000-member registry generated in-code with fixed seed (age,
  conditions, days-since-PCP, ER visits, meds, living situation,
  transportation need, missing screenings — plus revenue-adjacent fields
  that exist ONLY to be excluded).
- Featured member override: Margaret Ellis, 78, Type 2 Diabetes +
  Hypertension + Osteoarthritis, transportation need.
- 10 hand-authored assessment source lines; seeded 2025-cycle memory
  (cancellation learnings, claims-lag learning).
- 8 hand-labeled reconciliation eval cases.

**Outputs.**

- 265 members identified (need score ≥ 70 + care opportunity).
- Outreach/scheduling event timeline (cancel → rebook → completed visit).
- 10 findings classified reported/verified/care_gap + clinician flags +
  protocol validations.
- 3 tasks with authorized roles, constraints, and human-completed
  timelines (incl. the live denial).
- Reconciliation classification for the missing-claim discrepancy
  (EXPECTED_PROCESSING_DELAY → UNRESOLVED → re-check → human close).
- Operations dashboard + five self-eval dimensions.

**Constraints.** Stdlib only, fully offline, no API keys. Fixed seed +
fixed "today" → byte-identical output. Hard rules enforced IN CODE (assert
/ raise), not just promised in prose. Never claims health outcomes.

**Success criteria.** Self-eval dimensions hit their marks: prioritization
precision 99.6% (264/265), extraction 10/10 with 0 invented diagnoses,
reconciliation precision/recall 1.00 on 8/8 cases, routing 3/3 with 0
agent med changes, reliability 10/10 byte-identical runs.

**Definition of done.** The 7-step lifecycle prints end to end and exits 0;
README carries all 10 checklist sections; `TEST-LOG.md` shows the 10/10
determinism gate passing.

---

## Documented single-agent or multi-agent workflow

**Single-agent workflow** — one orchestrator (HHV Copilot) + specialized
tools + deterministic guardrails. Not six independent agents: validation
rules, authorization checks, and task-state transitions are deterministic
code, not LLM judgment. Memory (prior-cycle learnings) is recalled,
applied, and updated as the run proceeds.

```
                        ┌─────────────────────────────────────┐
                        │           HHV COPILOT               │
                        │         (orchestrator)              │
                        │  prints PLAN + every tool call      │
                        └──────────────┬──────────────────────┘
                                       │ uses
        ┌──────────────┬───────────────┼────────────────┬──────────────┐
        ▼              ▼               ▼                ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ ┌────────────┐
│load_registry│ │  identify_  │ │ schedule_   │ │  extract_    │ │ reconcile_ │
│             │ │  members    │ │  visit      │ │  findings    │ │  sources   │
│1,000 synth. │ │need-based;  │ │cancel→      │ │reported /    │ │3-source    │
│members,     │ │revenue      │ │rebook loop  │ │verified /    │ │investigate │
│fixed seed   │ │fields       │ │w/ memory    │ │care_gap      │ │→ classify  │
│             │ │EXCLUDED     │ │             │ │              │ │→ dispose   │
└─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘ └────────────┘
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        ▼              ▼ │              │ ▼              ▼
┌──────────────┐ ┌─────────────┐ │ ┌────────────┐ ┌─────────────┐
│  validate_   │ │create_task /│ │ │  Copilot   │ │   render_   │
│  protocols   │ │transition_  │ │ │  Memory    │ │  dashboard  │
│clinician     │ │task         │ │ │ 2025-cycle │ │ operations │
│flags; no     │ │human-only   │ │ │ learnings  │ │ only; no   │
│invented dx   │ │completion   │ │ │ recalled + │ │ outcome    │
│              │ │guardrail    │ │ │ stored     │ │ claims     │
└──────────────┘ └─────────────┘ │ └────────────┘ └─────────────┘
                                │
                    hard rules enforced IN CODE (assert / raise),
                    not just promised in prose
```

**The six hard rules** (the operating charter, stated before anything
runs): never high-utilization-only identification; never revenue-optimized
(revenue fields provably unread); never invent diagnoses (guardrail raises);
never change medications; only authorized humans complete tasks; never
claim health outcomes improved.

---

## Working prototype evidence, source code, and setup instructions

### Setup (MacBook, step by step)

You need nothing but Python 3, which ships with macOS.

**For the live browser demo (recommended on stage):** run `python3 app.py`
from the demo folder and open http://localhost:8002 in Chrome — see the
"Open in Chrome" quickstart at the top of this README. The steps below run
the same demo in the terminal instead.

**1. Open Terminal.** (Spotlight → type "Terminal" → Enter.)

**2. Check Python:**

```bash
python3 --version
```

Any Python 3.8+ works.

**3. Go to the demo folder:**

```bash
cd ~/workspace/agentic-ai-workshop/hhv-copilot
```

**4. Run the demo:**

```bash
python3 demo.py
```

That's it — no arguments, no installs. The full 7-step lifecycle plays end
to end in under a second and exits 0 on success. It's fully deterministic:
byte-identical output every run (see `TEST-LOG.md`), so it never surprises
you on stage.

**Prefer Chrome?** In step 4, run `python3 app.py` instead of
`python3 demo.py`, then open http://localhost:8002 in Chrome and press
**▶ Run live demo** — the same deterministic run renders in the browser,
with the orchestrator's plan highlighted and every tool call in the trace
panel.

### Files

| File | What it is |
|---|---|
| `demo.py` | The demo. Pure Python stdlib, zero dependencies. Prints the orchestrator plan, every tool call, memory operations, guardrail checks, the 7-step lifecycle, dashboard, and self-eval. |
| `app.py` | Localhost web UI for the live Chrome demo (stdlib `http.server` only). `python3 app.py` serves http://localhost:8002; the page runs `demo.py` and renders the plan, tool calls, and results in styled panels. |
| `requirements.txt` | Stdlib-only note — there is nothing to install. |
| `README.md` | This file: story, run steps, speaker notes, architecture. |
| `CHECKLIST.md` | Maps each of the 10 section headings to its checklist item. |
| `TEST-LOG.md` | 10 consecutive runs: exit code + SHA-256 per run. 10/10 byte-identical required. |
| `RUBRIC.md` | Self-score 1–5 per judging criterion with evidence, honest gaps, and how a student could close them — plus the five evaluation dimensions. |

### The demo script (with speaker notes)

Two ways to play the demo: click **▶ Run live demo** in the Chrome web UI
(`python3 app.py`, then open http://localhost:8002 — recommended on stage,
since the plan renders highlighted and every tool call lands in the trace
panel), or run `python3 demo.py` in the terminal. Either way the output is
byte-identical — narrate as follows. Approximate runtime: 6–7 minutes.

**Opening — the charter (~30 seconds)**

> **Say:** "Before anything runs, the agent states its operating charter —
> six hard rules. Notice these aren't suggestions in a prompt. They're
> enforced in code: the identifier provably can't read revenue fields, the
> diagnosis guardrail raises on violation, and in a minute you'll watch the
> agent get *denied* when it tries to close a task itself."

**Step 1 — Member Identification (~90 seconds)**

> **Say:** "One thousand synthetic members. The agent scores clinical need
> — age, conditions, how long since a PCP visit, polypharmacy, living
> alone, transportation need, missing screenings. Two hundred sixty-five
> make the outreach list."

Point at the guardrail line:

> **Say:** "Here's the part most demos skip. The data *contains* revenue
> signals — documented-diagnosis counts, risk-revenue estimates. The demo
> verifies at runtime that the identifier never references them. And watch
> what it refuses to do: ranking by ER visits alone overlaps our cohort by
> only 74 members. Eight high utilizers are excluded because they have *no
> care opportunity* — a recent PCP visit, no gaps. High use alone never
> qualifies anyone."

**Live-demo cue:** ask the room — *"If you built this at a health plan,
what would your boss pressure you to optimize for?"* Let them say
"revenue." Then: *"That's exactly what the guardrail is for."*

**Step 2 — Outreach & Scheduling (~60 seconds)**

> **Say:** "Our deep-dive member is Margaret Ellis, 78. Her visit was
> scheduled for September 5th — and she cancelled. Reason: no ride. Watch
> the loop: the agent investigates, recalls that the *2025 cycle* had the
> exact same cancellation for her, and rebooks September 12th *with
> transportation bundled*. The visit completes. A cancellation isn't a dead
> end; it's a signal with a memory attached."

**Step 3 — Assessment Interpretation (~90 seconds)**

> **Say:** "Ten findings, three buckets. *Reported* — she said it, we
> didn't verify it. *Verified* — measured or on record. *Care gap* —
> missing expected care. Three get clinician-review flags. And here's the
> discipline: her dizziness is *reported, cause undetermined* — the
> protocol says orthostatic vitals and a fall-risk assessment, and
> explicitly says *do not label it*. The agent doesn't diagnose. Ever."

**Step 4 — Care Gap Resolution (~60 seconds)**

> **Say:** "Three tasks: PCP follow-up, medication reconciliation,
> transportation. Every task names its authorized human. The med-rec task
> carries a constraint in all caps: the agent may not propose, change, or
> discontinue any medication."

**Live-demo cue:** point at the denial — *"And to prove the guardrail is
real, the agent tries to close the med-rec task itself — and gets denied.
This is decision support, not autonomous care."*

**Steps 5–6 — The injected discrepancy (~2 minutes, the centerpiece)**

> **Say:** "Now the part I want you to remember. The PCP follow-up:
> scheduling says completed, the vendor file arrived — but claims has
> nothing. Two options a naive system takes: close the task anyway, or
> declare the visit never happened. Our agent does a third thing: it
> *investigates*. Four checks — ID match, file integrity, date
> consistency, claims freshness. The claim is 8 days old; normal lag is 30
> to 45. Classification, *before* disposition: expected processing delay.
> The task goes UNRESOLVED — not closed, not failed. Absence of evidence is
> not evidence of absence."

Pause. Then:

> **Say:** "The October claims refresh arrives with the missing record. The
> agent reruns everything from scratch — trusts nothing — all three sources
> agree, and *then* a human, care coordinator Sam Reyes, closes the task.
> Every state change is on the timeline."

**Step 7 — Dashboard + self-eval (~45 seconds)**

> **Say:** "The dashboard reports operations: 265 identified, 151
> scheduled, 97 visits completed; tasks 2 closed, 1 still waiting on the
> pharmacist — honestly open. And read the bottom line with me: *these are
> operations metrics, not health outcomes. A completed visit is not a
> health outcome.* If your dashboard claims otherwise, it's lying."

Close with the five self-eval dimensions (they're printed):
prioritization precision 99.6%, extraction 10/10, reconciliation
precision/recall 1.00, routing 3/3, reliability 10/10 — "and the honest
limits right underneath."

---

## Functional and end-to-end testing, realistic scenarios, failure cases, reliability, and human oversight

**Realistic scenarios (end to end).** The full 7-step lifecycle on the
featured member: charter → 265-member identification → cancel→rebook loop
→ 10-finding interpretation → 3-task resolution (with live denial) → the
injected 3-source discrepancy → re-check on claims refresh → human close →
dashboard + self-eval.

**Failure cases the demo handles** (all from `demo.py` behavior):

- **Agent tries to close a task.** `transition_task` raises
  `PermissionError` when the actor is "HHV Copilot" — demonstrated live on
  the med-rec task. Only the authorized human (PCP, pharmacist, care
  coordinator) can set COMPLETED.
- **Invented diagnosis.** `guard_no_invented_diagnoses` scans every
  extracted finding against banned phrases ("diagnosed with", "has
  orthostatic hypotension", …) and raises instead of proceeding — hard rule
  #1 enforced in code.
- **Missing claim within the lag window.** Classified
  `EXPECTED_PROCESSING_DELAY` (8 days old vs 30–45 normal lag): task goes
  UNRESOLVED, re-checked on the next refresh — never closed on hope, never
  failed on absence.
- **Missing claim past the lag window.** Classified
  `UNVERIFIED_NO_EVIDENCE`: escalate to human review — do NOT assume care
  did or did not happen.
- **ID mismatch / bad file / date conflict / duplicates / source
  conflict.** The 8-case self-eval proves each classification fires on its
  own evidence pattern (8/8, precision/recall 1.00): ID_MISMATCH,
  FILE_INCOMPLETE, DATE_INCONSISTENCY, DUPLICATE_RECORDS, SOURCE_CONFLICT,
  CONSISTENT.
- **No care opportunity.** `has_care_opportunity` excludes high utilizers
  with a recent PCP visit and no gaps — high use alone never qualifies
  anyone for outreach.

**Reliability gate.** `TEST-LOG.md` records 10 consecutive runs of
`python3 demo.py` — exit codes + SHA-256 of full output — with the result
**10/10 PASSED, byte-identical output on every run**.

**Human oversight.** Every consequential state change names its authorized
human: tasks complete only by humans (the agent is denied in code);
reconciliation escalations go to humans; the dashboard reports operations,
never health outcomes. The demo's thesis line: *decision support, not
autonomous care.*

**The five evaluation dimensions (computed by the demo itself):**

| Dimension | Result | What it means |
|---|---|---|
| Prioritization agreement | precision 99.6% (264/265), recall 31.6% | Nearly every agent pick is also flagged by an independent care-manager checklist; the agent prioritizes within need rather than screening broadly |
| Extraction accuracy | 10/10, 0 invented diagnoses | All findings correctly classified reported/verified/care_gap on the scripted assessment |
| Reconciliation precision/recall | 1.00 / 1.00 (8/8 labeled cases) | The discrepancy classifier handles delay, ID mismatch, date conflict, incomplete/duplicate files, full agreement, and source conflict |
| Routing correctness | 3/3, 0 agent med changes | Every task routed to its correct authorized role; the agent never touches medications |
| Workflow reliability | 10/10 byte-identical runs | See `TEST-LOG.md` |

Honest limits (also printed by the demo): the registry is synthetic, the 8
eval cases are hand-labeled, extraction is validated on one scripted
assessment. See `RUBRIC.md` for the full self-assessment.

---

## Focus, feasibility, and avoidance of unnecessary complexity

One orchestrator, narrow tools, deterministic rules — stdlib only. Not
built:

- **No LLM calls.** The orchestrator's reasoning is explicit code, so the
  guardrails (assert/raise) are provably enforced — a prompt can't promise
  what code guarantees.
- **No real data integrations.** The 1,000-member registry is generated
  in-code; the three sources in the discrepancy demo are dicts. The lesson
  is the *classification-before-disposition* discipline, not ETL.
- **No outcome modeling.** The dashboard deliberately reports operations
  only; adding a health-outcomes claim would be the demo's cardinal sin.
- **No multi-agent sprawl.** Six stages run through one orchestrator with
  tool contracts — students see where the AI goes and where deterministic
  rules must hold, without a coordination layer to debug.

Feasibility: the whole lifecycle is ~1,100 lines a student can read in one
sitting — and the swap path (LLM for `extract_findings`, vector store for
`CopilotMemory`) keeps every guardrail in place.

---

## Interdisciplinary team roles and division of labor

| Role | Owns in this demo | Concrete component |
|---|---|---|
| **Domain researcher** | HHV program design and clinical discipline | Need-score formula (threshold 70), the six hard rules, protocol validations (A1C cadence, BP interpretation, dizziness = undetermined), the reported/verified/care-gap taxonomy, "never claim health outcomes" dashboard discipline |
| **Agent engineer** | Orchestrator, tools, and code-enforced guardrails | HHV Copilot orchestrator, `identify_members` / `extract_findings` / `reconcile_sources` tools, `guard_no_invented_diagnoses`, the `transition_task` PermissionError denial, `classify_discrepancy` |
| **Data engineer** | Synthetic registry and reconciliation fixtures | `generate_registry` (1,000 members, seed 20261010), `CopilotMemory` seed data, the 8 hand-labeled `RECON_EVAL_CASES`, claims-lag window constants |
| **UX / storyteller** | The 6–7 minute lifecycle narrative | Speaker notes (charter → identification → cancel/rebook → interpretation → denial → discrepancy centerpiece → dashboard), Margaret Ellis deep-dive, live-demo cues |
| **QA** | Reliability gate and the five self-eval dimensions | `TEST-LOG.md` 10/10 byte-identical gate, 8/8 reconciliation precision/recall, 10/10 extraction, 3/3 routing, the honest-limits disclosure |

---

## Limitations, risks, and responsible AI (ethics, privacy, security, safety)

- **Synthetic everything.** The 1,000-member registry, the assessment, the
  claims files — all invented. The demo's numbers demonstrate *method*,
  not real-world performance.
- **Revenue-guardrail lesson.** The demo exists partly to show what must
  be *refused*: revenue-optimized identification is the pressure a real
  plan would face, and the identifier provably can't read those fields.
- **Never invent diagnoses.** The guardrail raises on banned phrases — in
  production this needs clinician-authored phrase lists, review, and audit
  trails, not a demo constant.
- **Never claim health outcomes.** The dashboard reports operations (265
  identified, 151 scheduled, 97 visits). A completed visit is not a health
  outcome — the demo reads that line aloud.
- **Human authority is structural.** Tasks complete only by authorized
  humans; escalations go to humans; the agent is denied in code when it
  tries otherwise. Automation bias is the risk this architecture is built
  to contain.
- **Privacy by construction (demo).** All members are fictional; no real
  PHI appears. A production version would need HIPAA-grade access
  controls, audit logging, and minimum-necessary data handling — none of
  which a demo should fake.

---

## Practical value, adoption path, and measurable outcomes

**Practical value.** The HHV lifecycle's failure modes — wrong-member
outreach, invented findings, closed-on-missing-data tasks, outcome-claiming
dashboards — are where real programs lose trust and money. This demo is a
blueprint for the *disciplined* version: need-based identification with
revenue provably excluded, classify-before-disposition reconciliation, and
humans as the only terminal state.

**Adoption path** (from the demo's own "Extending it" notes):

1. Swap `extract_findings`' rules for an LLM call — keep the 3-way
   classification contract and the invented-diagnosis guardrail around it.
2. Give `CopilotMemory` a real persistent store and watch the
   cancel→rebook loop improve across cycles.
3. Add a ninth reconciliation case: what should happen when the *vendor*
   file contradicts the *member*? (Hint: new classification, human
   review.)
4. Add a `GuardrailAgent` tool that scans every planned disposition for
   charter violations before it executes.

**Measurable outcomes.** Today the demo measures itself: prioritization
precision 99.6%, extraction 10/10, reconciliation 1.00/1.00, routing 3/3,
reliability 10/10. A pilot would measure: outreach-list precision vs
care-manager review, cancellation→rebook conversion, task cycle time, and
discrepancy-resolution accuracy — operations metrics, never claimed health
outcomes.

---

*Built for the Agentic AI Workshop · Demo 5 of 5*
