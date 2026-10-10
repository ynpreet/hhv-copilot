#!/usr/bin/env python3
"""HHV Copilot -- localhost web UI (stdlib only).

Run:  python3 app.py   then open http://localhost:8002
Serves a guided, personalized tour of demo.py (the tested artifact --
demo.py is never modified here; it is only imported as a module and its
canned subprocess run is unchanged).
"""

import contextlib
import http.server
import io
import json
import mimetypes
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8002
HERE = Path(__file__).resolve().parent
DEMO_PY = HERE / "demo.py"

sys.path.insert(0, str(HERE))
import demo as DEMO  # the tested artifact: imported, never modified

# ---- personalized triage (app.py only; demo.py untouched) ----
# Red-flag patterns are checked FIRST -- any match escalates to URGENT and
# bypasses routine scoring entirely. This demo is not medical advice.

_CRITICAL_PATTERNS = [
    (r"\bcancer\b", "cancer"),
    (r"\btumou?rs?\b", "tumor"),
    (r"(4th|fourth)\s*stage|stage\s*(4|iv)\b", "advanced stage (stage 4/IV)"),
    (r"\bmetastatic\b", "metastatic disease"),
    (r"heart attack", "heart attack"),
    (r"\bstroke\b", "stroke"),
    (r"chest pain", "chest pain"),
    (r"difficulty breathing|can'?t breathe|shortness of breath|trouble breathing|can not breathe", "breathing difficulty"),
    (r"\bbleeding\b", "bleeding"),
    (r"\bseizure\b", "seizure"),
    (r"suicid|self-?harm|kill myself|end my life|end it all", "self-harm risk"),
    (r"\boverdose\b", "overdose"),
    (r"anaphyla", "anaphylaxis"),
]

_WELLNESS_PATTERNS = [
    r"\bi feel fine\b",
    r"\bfeeling (fine|great|good|healthy)\b",
    r"\bhealthy\b",
    r"\bno conditions\b",
    r"\bnone\b",
    r"\bnothing wrong\b",
    r"\ball good\b",
]

# (aliases, canonical display name, risk weight) -- checked in order.
_CONDITION_MAP = [
    (("type 1 diabetes", "t1d", "diabetes type 1"), "Type 1 Diabetes", 25),
    (("type 2 diabetes", "t2d", "diabetes type 2"), "Type 2 Diabetes", 20),
    (("diabetes",), "Type 2 Diabetes", 20),
    (("hypertension", "high blood pressure", "hbp", "htn", "high bp"), "Hypertension", 15),
    (("heart disease", "coronary", "heart failure", "chf"), "Heart Disease", 20),
    (("kidney disease", "ckd", "chronic kidney", "renal failure"), "Chronic Kidney Disease", 15),
    (("copd", "emphysema", "chronic bronchitis"), "COPD", 15),
    (("asthma",), "Asthma", 10),
    (("depression", "depressive"), "Depression", 10),
    (("anxiety",), "Anxiety", 8),
    (("hyperlipidemia", "high cholesterol", "cholesterol"), "High Cholesterol", 10),
    (("arthritis", "osteoarthritis", "rheumatoid"), "Arthritis", 5),
    (("migraine",), "Migraine", 5),
    (("obesity", "obese", "overweight"), "Obesity", 10),
    (("dementia", "alzheimer"), "Dementia", 10),
    (("seasonal allergies", "hay fever", "allergies", "allergy"), "Seasonal Allergies", 3),
    (("knee surgery", "hip surgery", "surgery", "post-surgery", "post surgery",
      "recovering from", "recovery from"), "Post-Surgery Recovery", 8),
    (("smoking", "smoker", "tobacco", "quit smoking", "vaping", "nicotine"), "Smoking Cessation", 10),
]

_HIGH_TIER_AT = 50
_MEDIUM_TIER_AT = 25

# Safe, general self-management information for recognized conditions that have
# no playbook entry in demo.py. General information only -- never prescriptive.
_EXTRA_SECTIONS = {
    "Type 1 Diabetes": [
        "Check blood sugar as your doctor advised and log the readings.",
        "Take insulin exactly as prescribed; never skip or adjust doses on your own.",
        "Know the signs of low blood sugar and keep fast-acting glucose nearby.",
    ],
    "Heart Disease": [
        "Take heart medications exactly as prescribed.",
        "Note any chest discomfort, unusual shortness of breath, or swelling -- report promptly.",
        "Ask your doctor what activity level is safe for you.",
    ],
    "COPD": [
        "Avoid smoke and strong fumes; make sure your inhaler technique is right.",
        "Notice changes in breathlessness or mucus -- report flare-ups early.",
        "Ask about pulmonary rehab and vaccinations (flu, pneumonia).",
    ],
    "Asthma": [
        "Keep your reliever inhaler where you can reach it.",
        "Learn your personal triggers and note them.",
        "Follow the asthma action plan you made with your doctor.",
    ],
    "Depression": [
        "Stay connected -- tell someone you trust how you are feeling.",
        "Keep a regular sleep schedule; daylight and gentle movement help.",
        "If thoughts of self-harm arise, call or text 988 (US) right away.",
    ],
    "Anxiety": [
        "Practice slow breathing when anxiety spikes; note what triggers it.",
        "Keep caffeine and alcohol in check -- both can worsen anxiety.",
        "If anxiety interferes with daily life, ask your doctor about options.",
    ],
    "High Cholesterol": [
        "Take cholesterol medication as prescribed, if any.",
        "Favor vegetables, whole grains, and lean proteins; limit fried foods.",
        "Recheck lipids on the schedule your doctor sets.",
    ],
    "Arthritis": [
        "Keep joints moving with gentle, doctor-approved activity.",
        "Use heat or cold for stiffness as advised.",
        "Report new swelling or hot-feeling joints to your care team.",
    ],
    "Migraine": [
        "Track attacks: when they start, how long they last, possible triggers.",
        "Rest in a dark, quiet room during an attack if you can.",
        "If attacks are frequent or suddenly different, tell your doctor.",
    ],
    "Obesity": [
        "Aim for small, steady changes in eating and activity -- not crash diets.",
        "Track weight weekly, same time of day.",
        "Ask your doctor about programs covered by your plan.",
    ],
    "Dementia": [
        "Keep a consistent daily routine; labels on rooms and drawers help.",
        "Caregivers: take breaks and ask about respite support -- burnout is real.",
        "Report sudden confusion changes promptly; they can signal something treatable.",
    ],
    "Seasonal Allergies": [
        "Check local pollen counts and limit outdoor time on high days.",
        "Shower and change clothes after being outside.",
        "If breathing is ever affected, treat it as urgent -- not just allergies.",
    ],
    "Post-Surgery Recovery": [
        "Follow your surgeon's wound-care and activity instructions exactly.",
        "Watch for redness, swelling, fever, or unusual pain -- report promptly.",
        "Do your prescribed rehab exercises even when they are uncomfortable.",
    ],
    "Smoking Cessation": [
        "Set a quit date and tell someone about it.",
        "Ask your doctor about quit aids covered by your plan.",
        "Cravings pass in minutes -- have a walk or a glass of water ready.",
    ],
}

_GENERIC_STEPS = [
    "Keep a simple symptom diary: what you feel, when, and what seems to help.",
    "Keep an up-to-date list of medications and bring it to every appointment.",
    "If symptoms worsen or worry you, contact your care team promptly.",
]

_WELLNESS_STEPS = [
    "Keep your annual checkup -- prevention beats treatment.",
    "Stay current on age-appropriate screenings (your doctor can list them).",
    "If anything changes, come back and tell us -- we will triage you then.",
]

_URGENT_HANDOFF_STEPS = [
    "Contact your doctor, specialist, or care team right away -- today, not next week.",
    "If symptoms are severe, new, or getting worse, call emergency services (911 in the US) or go to urgent care now.",
    "Do not wait for an email or app message for anything urgent -- call.",
    "Bring your medication list and recent test results to every appointment.",
]


def _parse_phrases(raw):
    """Split free text into condition phrases. Never iterate characters."""
    phrases = []
    for part in re.split(r"[;,]", raw.lower()):
        for q in re.split(r"\s+and\s+|\s*&\s*|\s+plus\s+", part):
            q = q.strip(" .")
            if q:
                phrases.append(q)
    seen, deduped = set(), []
    for q in phrases:
        if q not in seen:
            seen.add(q)
            deduped.append(q)
    return deduped


def _map_phrase(phrase):
    for aliases, display, weight in _CONDITION_MAP:
        for a in aliases:
            if a in phrase:
                return display, weight
    return None, 0


def _build_plan(display_names, tier, unknown):
    plan = []
    for dn in display_names:
        steps = DEMO.CONDITION_PLAYBOOKS.get(dn) or _EXTRA_SECTIONS.get(dn)
        if steps:
            plan.append({"condition": dn, "steps": list(steps)})
    if tier == "HIGH":
        plan.append({"condition": "High-risk follow-up",
                     "steps": ["Care manager will check in within 7 days.",
                               "If any symptoms worsen, call the clinic same-day."]})
    elif tier == "MEDIUM":
        plan.append({"condition": "Routine follow-up",
                     "steps": ["Care manager will check in within 30 days."]})
    if not plan or unknown or tier == "NEEDS REVIEW":
        plan.append({"condition": "General guidance (confirm with your care team)",
                     "steps": list(_GENERIC_STEPS)})
    return plan


def _print_pipeline(name, email, chan, display_names, tier, score, reasons, plan):
    patient = {
        "id": "WEB-001",
        "name": name,
        "age": 50,
        "email": email,
        "conditions": display_names,
        "last_visit": "not provided",
        "preferred_channel": chan,
        "risk_factors": {"from_user_input": True},
    }
    triage = {"tier": tier, "score": score, "reasons": reasons}
    print(f"[AuthAgent]    Login verified: {email}")
    print(f"[TriageAgent]  Scoring risk for {name} (conditions: {', '.join(display_names)})...")
    print(f"[TriageAgent]  Score {score} -> tier {tier}")
    for r in reasons:
        print(f"               - {r}")
    channel = DEMO.channel_agent(patient, triage)
    print(f"[ChannelAgent] Selected channel: {channel.upper()} (patient preference: {chan})")
    print(f"[CarePlanAgent] Assembled {len(plan)} care-plan section(s)")
    message = DEMO.message_agent(patient, triage, plan, channel)
    print(f"[MessageAgent] Rendered {channel.upper()} message:")
    print()
    print("-" * 72)
    print(message)
    print("-" * 72)

def _capture_canned():
    """Run the canned demo exactly as before (subprocess), capture stdout."""
    proc = subprocess.run(
        [sys.executable, str(DEMO_PY)],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        timeout=600,
    )
    return proc.stdout or proc.stderr

def _capture_fn(fn, params):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            return fn(params)
    except Exception as exc:  # never crash the page on a bad input
        return "[web-ui] The personalized run hit an error and stopped safely.\n%s: %s" % (type(exc).__name__, exc)

# _capture_custom: personalized handlers may return a dict carrying a follow-up decision.
def _capture_custom(fn, params):
    try:
        res = fn(params)
    except Exception as exc:  # never crash the page on a bad input
        return {"output": "[web-ui] The personalized run hit an error and stopped safely.", "decision": None}
    if isinstance(res, dict):
        res.setdefault("decision", None)
        return res
    return {"output": res, "decision": None}

# ---- personalized run: input handling lives in app.py; demo.py untouched ----

_HHV = {}
def _hhv_data():
    if "registry" not in _HHV:
        _HHV["registry"] = DEMO.generate_registry(1000)
        _HHV["identified"] = DEMO.identify_members(_HHV["registry"])
        _HHV["ids"] = set(m["member_id"] for m in _HHV["identified"])
    return _HHV["registry"], _HHV["identified"], _HHV["ids"]

def _reasons(m):
    try:
        _score, reasons = DEMO.need_score(m)
    except Exception:
        reasons = []
    return [str(x) for x in reasons]

def hhv_decision_table():
    registry, identified, ids = _hhv_data()
    rows = []
    for m in identified[:5]:
        rows.append({
            "member": f'{m["member_id"]} · {m["name"]}, {m["age"]}',
            "why": "; ".join(_reasons(m)) or "scored high on need",
            "rec": "VISIT",
            "reason": "Top of the need-based outreach list — a real care opportunity to review.",
        })
    feat = next(m for m in registry if m["member_id"] == "HHV-M0042")
    rows.append({
        "member": "HHV-M0042 · Margaret Ellis, 78",
        "why": "; ".join(_reasons(feat)) or "featured deep-dive member",
        "rec": "VISIT",
        "reason": "Featured deep-dive member: followed end to end through scheduling, cancellation, and rebooking.",
    })
    skipped = 0
    for m in DEMO.utilization_ranking(registry, 40):
        if m["member_id"] not in ids and skipped < 2:
            rows.append({
                "member": f'{m["member_id"]} · {m["name"]}, {m["age"]}',
                "why": f'{m["er_visits_12mo"]} ER visits, {m["admissions_12mo"]} admissions in 12 months',
                "rec": "SKIP",
                "reason": "High utilization alone never qualifies — recent PCP care and no open care gaps.",
            })
            skipped += 1
    return rows

def _to_int(v, default=0):
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return default

_HHV_STATS = {}

def _hhv_stats():
    # Distribution facts about the deterministic registry, for hints and
    # empty-state guidance. Computed once from the same data the UI serves.
    if not _HHV_STATS:
        registry, _, _ = _hhv_data()
        _HHV_STATS.update({
            "age75": sum(1 for m in registry if m["age"] >= 75),
            "age85": sum(1 for m in registry if m["age"] >= 85),
            "cond2": sum(1 for m in registry if len(m["conditions"]) >= 2),
            "cond3": sum(1 for m in registry if len(m["conditions"]) >= 3),
            "cond4": sum(1 for m in registry if len(m["conditions"]) >= 4),
            "max_cond": max(len(m["conditions"]) for m in registry),
            "days180": sum(1 for m in registry if m["days_since_pcp"] >= 180),
            "days365": sum(1 for m in registry if m["days_since_pcp"] >= 365),
            "max_days": max(m["days_since_pcp"] for m in registry),
            "max_age": max(m["age"] for m in registry),
            "ride": sum(1 for m in registry if m["transportation_need"]),
        })
    return _HHV_STATS

def hhv_filter(params):
    registry, _identified, ids = _hhv_data()
    stats = _hhv_stats()
    min_age = _to_int(params.get("min_age"))
    min_cond = _to_int(params.get("min_cond"))
    min_days = _to_int(params.get("min_days"))
    need_ride = (params.get("transport") or "") == "yes"

    def ok_age(m, v):
        return m["age"] >= v

    def ok_cond(m, v):
        return len(m.get("conditions", [])) >= v

    def ok_days(m, v):
        return m.get("days_since_pcp", 0) >= v

    def ok_ride(m, r):
        return (not r) or m.get("transportation_need")

    def count(a=True, co=True, d=True, r=True,
              av=None, cov=None, dv=None, rv=None):
        av = min_age if av is None else av
        cov = min_cond if cov is None else cov
        dv = min_days if dv is None else dv
        rv = need_ride if rv is None else rv
        n = 0
        for m in registry:
            if a and not ok_age(m, av):
                continue
            if co and not ok_cond(m, cov):
                continue
            if d and not ok_days(m, dv):
                continue
            if r and not ok_ride(m, rv):
                continue
            n += 1
        return n

    rows = []
    for m in registry:
        if not (ok_age(m, min_age) and ok_cond(m, min_cond)
                and ok_days(m, min_days) and ok_ride(m, need_ride)):
            continue
        if m["member_id"] in ids:
            score, _ = DEMO.need_score(m)
            rows.append({
                "member": f'{m["member_id"]} · {m["name"]}, {m["age"]}',
                "why": "; ".join(_reasons(m)) or "scored high on need",
                "rec": "VISIT",
                "reason": "On the need-based outreach list — worth your review.",
                "_score": score,
            })
        else:
            rows.append({
                "member": f'{m["member_id"]} · {m["name"]}, {m["age"]}',
                "why": f'{m["er_visits_12mo"]} ER visits, {m["admissions_12mo"]} admissions in 12 months',
                "rec": "SKIP",
                "reason": "Not on the outreach list — below the need threshold or no open care opportunity.",
                "_score": -1,
            })
    rows.sort(key=lambda r: r["_score"], reverse=True)
    for r in rows:
        r.pop("_score", None)
    shown = rows[:25]
    matched = len(rows)
    note = f"{matched} of 1,000 members matched your filters; showing top {len(shown)} by need score."

    extra = {"matched": matched}
    if matched == 0:
        solo = {
            "Minimum age": count(co=False, d=False, r=False),
            "Minimum conditions": count(a=False, d=False, r=False),
            "Days since PCP visit": count(a=False, co=False, r=False),
        }
        if need_ride:
            solo["Transportation need"] = count(a=False, co=False, d=False)
        tightest = min(solo, key=solo.get)
        relax = []
        if min_cond > stats["max_cond"]:
            mc = stats["max_cond"]
            relax.append({
                "desc": "Lower minimum conditions to %d (the most any member has)" % mc,
                "field": "f_cond", "value": str(mc), "count": count(cov=mc)})
        if min_age > stats["max_age"]:
            ma = stats["max_age"]
            relax.append({
                "desc": "Lower minimum age to %d (the oldest member)" % ma,
                "field": "f_age", "value": str(ma), "count": count(av=ma)})
        if min_days > stats["max_days"]:
            md = stats["max_days"]
            relax.append({
                "desc": "Lower days-since-PCP to %d (the longest gap in the data)" % md,
                "field": "f_pcp", "value": str(md), "count": count(dv=md)})
        relax.append({"desc": "Drop the minimum-age filter",
                      "field": "f_age", "value": "0", "count": count(a=False)})
        relax.append({"desc": "Drop the minimum-conditions filter",
                      "field": "f_cond", "value": "0", "count": count(co=False)})
        relax.append({"desc": "Drop the days-since-PCP filter",
                      "field": "f_pcp", "value": "0", "count": count(d=False)})
        if need_ride:
            relax.append({"desc": "Drop the transportation filter",
                          "field": "f_trans", "value": "", "count": count(r=False)})
        relax.sort(key=lambda o: o["count"], reverse=True)
        relax = [o for o in relax if o["count"] > 0][:2]
        extra["empty_help"] = {
            "per_filter": solo,
            "tightest": tightest,
            "tightest_count": solo[tightest],
            "relax": relax,
        }
    return shown, note, extra

PAGE = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>HHV Copilot &mdash; Live Demo</title>\n<style>\n:root{\n  --bg:#0b1220; --bg2:#0e1626; --panel:#131e33; --panel2:#182742;\n  --ink:#eaf0f9; --muted:#9db0c9; --faint:#6b7f99;\n  --teal:#2dd4bf; --teal-dim:rgba(45,212,191,.12);\n  --accent:#5aa9ff; --warn:#fbbf24; --danger:#f87171; --ok:#34d399;\n  --line:#233451; --radius:14px;\n}\n*{box-sizing:border-box}\nbody{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;\n  background:var(--bg);color:var(--ink);line-height:1.6}\nheader{background:linear-gradient(135deg,#0a2540 0%,#0e3a5c 60%,#0b4f4a 100%);\n  padding:42px 32px 34px;border-bottom:1px solid var(--line)}\n.wrap{max-width:1060px;margin:0 auto}\nheader h1{margin:0 0 8px;font-size:30px;letter-spacing:-.01em}\nheader .sub{margin:0;color:#c8d6ea;font-size:16px;max-width:800px}\n.badge{display:inline-block;margin-top:14px;font-size:11.5px;letter-spacing:.1em;\n  text-transform:uppercase;color:#06281f;background:var(--teal);\n  padding:5px 14px;border-radius:999px;font-weight:800}\nmain{padding:8px 32px 48px}\nsection.card{background:var(--panel);border:1px solid var(--line);\n  border-radius:var(--radius);padding:26px 28px;margin:26px 0}\nsection.card h2{margin:0 0 12px;font-size:18px;color:var(--teal)}\nsection.card h2 .n{display:inline-block;width:28px;height:28px;border-radius:50%;\n  background:var(--teal-dim);border:1px solid var(--teal);color:var(--teal);\n  text-align:center;line-height:26px;font-size:14px;margin-right:10px}\nsection.card p{margin:0 0 12px;color:#d5e0f1;font-size:15.5px}\nsection.card p:last-child{margin-bottom:0}\n.watch{list-style:none;margin:6px 0 0;padding:0}\n.watch li{position:relative;padding:8px 0 8px 30px;color:#d5e0f1;font-size:15px;\n  border-bottom:1px dashed var(--line)}\n.watch li:last-child{border-bottom:0}\n.watch li::before{content:"\\25b8";position:absolute;left:8px;color:var(--teal);font-weight:700}\nlabel.f{display:block;margin:14px 0 6px;font-size:13px;font-weight:700;\n  letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}\ninput[type=text],input[type=number],select,textarea{\n  width:100%;background:var(--bg2);border:1px solid var(--line);color:var(--ink);\n  border-radius:10px;padding:11px 14px;font-size:15px;font-family:inherit}\ntextarea{min-height:76px;resize:vertical}\ninput:focus,select:focus,textarea:focus{outline:none;border-color:var(--teal)}\n.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}\n@media(max-width:700px){.row2{grid-template-columns:1fr}}\n.btnrow{display:flex;gap:14px;align-items:center;margin-top:20px;flex-wrap:wrap}\nbutton.run{background:linear-gradient(135deg,#14b8a6,#0d9488);border:0;\n  color:#04211c;font-weight:800;font-size:17px;padding:15px 34px;\n  border-radius:12px;cursor:pointer;box-shadow:0 6px 22px rgba(45,212,191,.25)}\nbutton.run:hover{filter:brightness(1.08)}\nbutton.run:disabled{opacity:.45;cursor:default;box-shadow:none}\nbutton.ghost{background:transparent;border:1px solid var(--teal);color:var(--teal);\n  font-weight:700;font-size:15px;padding:13px 26px;border-radius:12px;cursor:pointer}\nbutton.ghost:hover{background:var(--teal-dim)}\nbutton.ghost:disabled{opacity:.45;cursor:default}\n.hint{color:var(--muted);font-size:13.5px}\n.spinner{display:none;align-items:center;gap:10px;color:var(--muted);font-size:14px;margin-top:14px}\n.spinner.show{display:flex}\n.dot{width:12px;height:12px;border-radius:50%;background:var(--teal);\n  animation:pulse 1s infinite ease-in-out}\n@keyframes pulse{0%,100%{transform:scale(.6);opacity:.5}50%{transform:scale(1.2);opacity:1}}\n#output{display:none;margin-top:6px}\n#output.show{display:block}\n.out{background:#0a0f1c;border:1px solid var(--line);border-radius:12px;\n  padding:20px 22px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;\n  font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;\n  max-height:640px;overflow:auto;color:#c9d6ea}\n.sechead{color:var(--accent);font-weight:800;margin:18px 0 2px;font-size:13.5px}\n.sechead:first-child{margin-top:0}\n.seccap{background:var(--teal-dim);border-left:3px solid var(--teal);\n  padding:8px 12px;margin:4px 0 12px;border-radius:0 8px 8px 0;\n  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;\n  font-size:13.5px;color:#bfe9e2}\n.tok-orch{color:var(--accent);font-weight:700}\n.tok-tool{color:var(--ok);font-weight:700}\n.tok-guard{color:var(--warn);font-weight:700}\n.tok-mem{color:#c084fc;font-weight:700}\n#takeaways{display:none}\n#takeaways.show{display:block}\n.take{background:rgba(52,211,153,.07);border:1px solid rgba(52,211,153,.4);\n  border-radius:var(--radius);padding:22px 26px;margin:26px 0}\n.take h2{color:var(--ok);margin:0 0 10px;font-size:18px}\n.take ul{margin:0;padding-left:20px}\n.take li{margin:8px 0;color:#d5e0f1;font-size:15px}\ntable.dec{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}\ntable.dec th{background:var(--panel2);color:var(--teal);text-align:left;\n  padding:10px 12px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;\n  border-bottom:1px solid var(--line)}\ntable.dec td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}\n.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-weight:800;font-size:12px}\n.pill.v{background:var(--ok);color:#04281c}\n.pill.s{background:var(--faint);color:#0b1220}\nfooter{padding:26px 32px 40px;color:var(--faint);font-size:13.5px;text-align:center}\nfooter a{color:var(--teal);text-decoration:none}\nfooter a:hover{text-decoration:underline}\ndetails.raw{margin-top:14px}\ndetails.raw summary{cursor:pointer;color:var(--muted);font-size:13.5px}\n\n/* --- hhv revamp: filter hints + guided empty state --- */\n.fhint{color:var(--faint);font-size:12.5px;margin-top:6px}\n.emptyhelp{background:rgba(251,191,36,.06);border:1px solid rgba(251,191,36,.35);\n  border-radius:var(--radius);padding:16px 20px;margin-top:14px}\n.emptyhelp p{margin:0 0 10px}\n.emptyhelp .btnrow{margin-top:6px}\n#tableModeLabel{margin-top:0}\n\n/* --- care revamp: why-section + sidebar layout --- */\n.care-layout{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:26px;align-items:start}\n.care-main{min-width:0}\n.care-sidebar{position:sticky;top:20px;min-width:0}\n@media(max-width:960px){.care-layout{grid-template-columns:1fr}.care-sidebar{position:static}}\n.side-card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:20px;margin-bottom:20px}\n.side-card h3{margin:0 0 10px;font-size:15px;color:var(--teal)}\n.side-vid{margin-bottom:18px}\n.side-vid:last-child{margin-bottom:0}\n.side-vid iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:10px;display:block;background:#000}\n.side-vid p{font-size:13px;color:var(--muted);margin:8px 0 0;line-height:1.5}\n.why-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin:16px 0}\n@media(max-width:700px){.why-grid{grid-template-columns:1fr}}\n.why-grid figure{margin:0}\n.why-grid img{width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:10px;border:1px solid var(--line);display:block;background:#0a0f1c}\n.why-grid figcaption{font-size:12.5px;color:var(--muted);margin-top:6px;line-height:1.5}\n.chips{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 4px}\n.chip{background:var(--panel2);border:1px solid var(--teal);color:var(--teal);font-size:13px;padding:7px 14px;border-radius:999px;cursor:pointer;font-family:inherit;line-height:1.4}\n.chip:hover{background:var(--teal-dim)}\n.chal{list-style:none;margin:10px 0 0;padding:0}\n.chal li{position:relative;padding:7px 0 7px 28px;color:#d5e0f1;font-size:15px}\n.chal li::before{content:"!";position:absolute;left:9px;color:var(--warn);font-weight:800}\n\n\n.blog-list{list-style:none;margin:0;padding:0}\n.blog-list li{margin:0 0 14px;padding-bottom:14px;border-bottom:1px dashed var(--line)}\n.blog-list li:last-child{margin-bottom:0;padding-bottom:0;border-bottom:0}\n.blog-list a{color:var(--teal);font-weight:700;font-size:14.5px;text-decoration:none}\n.blog-list a:hover{text-decoration:underline}\n.blog-list span{display:block;font-size:13px;color:var(--muted);margin-top:3px;line-height:1.5}</style>\n</head>\n<body>\n<header><div class="wrap">\n  <h1>HHV Copilot</h1>\n  <p class="sub">You decide who gets a nurse visit — the agent does the homework.</p>\n</div></header>\n<main><div class="wrap care-layout">\n<div class="care-main">\n<section class="card" id="why">\n<h2><span class="n">&#9733;</span>Why this matters in real life</h2>\n<p>Most seniors want to keep living at home &mdash; it is where they feel independent, comfortable, and themselves. But a home with chronic conditions, a dozen medications, and no recent doctor visit is also where small problems quietly become emergencies.</p>\n<p>That is why Medicare Advantage plans send nurses for in-home assessments: a calm, unhurried visit that spots the risks a 15-minute clinic appointment misses &mdash; fall hazards, missed medications, uncontrolled conditions, loneliness. Catching these early means simpler, kinder interventions instead of an ambulance later.</p>\n<p>The hard part is scale: a plan may have thousands of members and only so many nurses. Deciding <b>who gets a visit, and in what order</b> &mdash; fairly, with a reason for every name &mdash; is the real operational challenge. That is exactly what this demo practices: you are the decision-maker, the agent is your analyst.</p>\n<div class="why-grid">\n<figure><img src="/assets/img/nurse-visit.svg" alt="Nurse visiting a patient at home" loading="lazy"><figcaption>A nurse home visit: unhurried, observant, personal.</figcaption></figure>\n<figure><img src="/assets/img/senior-home.svg" alt="Senior enjoying life at home" loading="lazy"><figcaption>Home is where most seniors want to stay &mdash; independence matters.</figcaption></figure>\n<figure><img src="/assets/img/home-nurse.svg" alt="Home nurse caring for a patient" loading="lazy"><figcaption>One-on-one attention catches what rushed appointments miss.</figcaption></figure>\n<figure><img src="/assets/img/caregiver.svg" alt="Caregiver supporting an older adult" loading="lazy"><figcaption>Support that keeps people safe where they are.</figcaption></figure>\n</div>\n<p><b>Why this kind of agent helps:</b></p>\n<ul class="watch">\n<li>Finds the members most likely to benefit &mdash; not just the loudest or most expensive</li>\n<li>Gives a plain-English reason for every visit recommendation, so a human can approve with confidence</li>\n<li>Deliberately skips members who would not benefit &mdash; saying &ldquo;no visit&rdquo; is also a decision</li>\n</ul>\n</section>\n\n<section class="card" id="story">\n  <h2><span class="n">1</span>The story</h2>\n  <p>You work at a Medicare Advantage plan. You have <b>1,000 members</b> and a limited number of nurse home visits. Every visit costs money; every missed care gap costs more. <b>You decide who gets one.</b></p>\n<p>This demo is your rehearsal. An AI copilot screens all 1,000 members and hands you a prioritized outreach list — with reasons. It handles the scheduling (including the member who cancels), interprets the nurse\'s assessment without inventing diagnoses, chases every care gap until a human closes it, reconciles messy data across three systems, and reports honestly on what actually got done.</p>\n</section>\n\n<section class="card" id="watch">\n  <h2><span class="n">2</span>What to watch for</h2>\n  <ul class="watch">\n<li>Watch Step 1: 1,000 members screened, 265 recommended — and 8 heavy ER users deliberately <b>excluded</b>. High use alone never qualifies anyone.</li>\n<li>Watch the cancellation in Step 2: the member cancels, and instead of giving up, the agent remembers last year\'s lesson and rebooks with a ride bundled.</li>\n<li>Watch Step 5, the injected problem: the PCP record is missing from claims. The agent investigates instead of assuming — and marks the task UNRESOLVED, not failed.</li>\n<li>After the run, open the Decision Table below: every recommendation with its reason, plus members the agent says to skip.</li>\n  </ul>\n</section>\n\n\n<section class="card" id="howdecided">\n  <h2><span class="n">✓</span>How the decision gets made</h2>\n  <p>The agent <b>recommends</b>. <b>You</b> approve. That is the entire governance model, and it is enforced in the design: the copilot never schedules a visit on its own, never sends a nurse, and never closes a task — every consequential step waits for an authorized human.</p>\n  <p style="margin-top:10px"><b>VISIT</b> means <i>“worth your review”</i>: the member cleared a need-based score with a real care opportunity. <b>SKIP</b> means <i>“the data says no care opportunity”</i>: 8 of the heaviest ER users were skipped precisely because high use alone never qualifies — without a care gap, there is nothing a nurse visit would fix.</p>\n</section>\n\n\n<section class="card" id="tryown">\n  <h2><span class="n">✎</span>Try your own — explore the outreach list</h2>\n  <p>You are the plan manager. Filter the 1,000-member registry with <b>your</b> criteria and see who the agent recommends for a visit — and who it says to skip.</p>\n  <div class="row2">\n    <div><label class="f" for="f_age">Minimum age</label><input type="number" id="f_age" value="75" min="0" max="110"><div class="fhint">Aged 75+: 689 / 85+: 338</div></div>\n    <div><label class="f" for="f_cond">Minimum number of conditions</label><input type="number" id="f_cond" value="2" min="0" max="4"><div class="fhint">2+: 712 / 3+: 406 / 4+: 117 (most any member has: 4)</div></div>\n  </div>\n  <div class="row2">\n    <div><label class="f" for="f_pcp">Days since last PCP visit (minimum)</label><input type="number" id="f_pcp" value="180" min="0" max="540"><div class="fhint">180+ days: 657 / 365+ days: 321</div></div>\n    <div><label class="f" for="f_trans">Transportation need</label>\n      <select id="f_trans"><option value="">No preference</option><option value="yes">Yes — needs a ride</option></select><div class="fhint">Need a ride: 273 of 1,000</div></div>\n  </div>\n  <div class="btnrow">\n    <button class="ghost" id="filterRun">Apply my filters</button>\n    <span class="hint">Top 25 matches by need score. Same inputs → same output.</span>\n  </div>\n  <div class="spinner" id="fspin"><div class="dot"></div>Re-slicing the registry…</div>\n  <div id="filterNote"></div>\n</section>\n<section class="card" id="dectable" style="display:none">\n  <h2><span class="n">⚖</span>The decision table — who gets a visit</h2>\n  <p id="tableModeLabel" class="hint"></p>\n  <div id="decisionTable"></div>\n</section>\n\n\n<section class="card" id="runbox">\n  <h2><span class="n">3</span>Run the demo</h2>\n  <p>Click below to run the full canned demonstration. It takes a few seconds.</p>\n  <div class="btnrow">\n    <button class="run" id="run">&#9654; Run live demo</button>\n  </div>\n  <div class="spinner" id="spin"><div class="dot"></div><span>The copilot is running the 7-step lifecycle…</span></div>\n  <div id="output">\n    <div class="out" id="outtext"></div>\n    <details class="raw"><summary>Show raw terminal output</summary>\n      <div class="out" id="rawtext"></div>\n    </details>\n  </div>\n</section>\n\n<section class="card" id="takeaways" style="display:none">\n  <div class="take">\n    <h2>What just happened</h2>\n    <ul>\n<li>265 of 1,000 members made your outreach list — picked for care need, not revenue. The 8 highest ER users were skipped on purpose.</li>\n<li>One member (Margaret Ellis, 78) was followed end to end: identified, scheduled, cancelled, rebooked with a ride, visited, assessed.</li>\n<li>Three care gaps became three tracked tasks. The medication task stayed open until the pharmacist acted — the agent never closes what a human hasn\'t done.</li>\n<li>The missing PCP record was the real test: investigated, classified as expected processing delay, marked UNRESOLVED. Absence of evidence is not evidence of absence.</li>\n<li>The dashboard shows cost versus what got done — and refuses to claim health outcomes it didn\'t measure.</li>\n    </ul>\n  </div>\n</section>\n\n</div>\n<aside class="care-sidebar">\n<div class="side-card">\n<h3>Learn more</h3>\n<p style="font-size:13.5px;color:var(--muted);margin:0 0 14px">Want to go deeper on home-based care? Start with these.</p>\n<div class="side-vid">\n<iframe src="https://www.youtube-nocookie.com/embed/KH_0sSI-SpY" title="Why Medicare Advantage Plans Keep Calling" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n<p>What in-home assessments are, why plans do them, and what actually happens during a visit.</p>\n</div>\n<div class="side-vid">\n<iframe src="https://www.youtube-nocookie.com/embed/rTMzosrr-q8" title="Does Medicare Pay for Home Health Care?" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n<p>What the home-health benefit really covers &mdash; and the single most expensive misunderstanding about it.</p>\n</div>\n<div class="side-vid">\n<iframe src="https://www.youtube-nocookie.com/embed/IsWEgeIQZ-A" title="The Medicare Home Health Benefit, Drawn Out" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n<p>A hand-drawn explainer: what qualifies, what is excluded, and what to ask first.</p>\n</div>\n</div>\n<div class="side-card">\n<h3>Go deeper &mdash; articles</h3>\n<ul class="blog-list">\n<li><a href="https://www.homeinstead.com/home-care/usa/or/beaverton/805/cost-of-care-for-aging-adults/in-home-care-benefits-for-seniors/" target="_blank" rel="noopener">Benefits of Senior Home Care</a><span>Home Instead &mdash; Why aging in place works: independence, one-on-one attention, staying connected.</span></li>\n<li><a href="https://www.h2hhc.com/blog/the-benefits-of-home-health-care-for-aging-in-place" target="_blank" rel="noopener">The Benefits of Home Health Care for Aging in Place</a><span>H2HHC &mdash; How in-home care reduces hospital risk and keeps seniors safe at home.</span></li>\n<li><a href="https://www.thevisitingnurses.com/exploring-the-benefits-of-home-care-for-seniors-aging-in-place/" target="_blank" rel="noopener">Exploring the Benefits of Home Care for Seniors</a><span>Visiting Nurses &mdash; Independence, family bonds, and what good home care actually looks like.</span></li>\n</ul>\n</div>\n</aside>\n\n</div></main>\n<footer><div class="wrap">\n  <a href="https://github.com/ynpreet/hhv-copilot" target="_blank" rel="noopener">View the project on GitHub</a>\n  &nbsp;&middot;&nbsp; All data in this demo is synthetic / fictional.\n</div></footer>\n\n<script>\nconst SECTIONS = [["STEP 1/7", "Member identification: need-based scoring across 1,000 members. Revenue fields exist in the data and are deliberately never read."], ["STEP 2/7", "Outreach &amp; scheduling: the member cancels \\u2014 the agent recalls last year\'s lesson and rebooks smarter, with a ride bundled."], ["STEP 3/7", "Assessment interpretation: findings extracted as reported vs. verified vs. care gap. Nothing invented, nothing assumed."], ["STEP 4/7", "Care gap resolution: three tasks created \\u2014 PCP follow-up, medication reconciliation, transportation. The agent coordinates; humans close."], ["STEP 5/7", "The injected problem: the PCP follow-up record is missing from claims. Watch the agent investigate four checks instead of assuming."], ["STEP 6/7", "Resolution: the updated claims file arrives, the agent re-checks, and the task moves \\u2014 closed by a human, not the agent."], ["STEP 7/7", "Program dashboard: visits, tasks, bottlenecks \\u2014 operations metrics, honestly labeled as NOT health outcomes."], ["SELF-EVALUATION", "The agent grades itself on five dimensions \\u2014 and lists its honest limits in plain language."], ["DEMO COMPLETE", "End of run. Below: your decision table and takeaways."]];\nfunction esc(s){return s.replace(/&/g,\'&amp;\').replace(/</g,\'&lt;\').replace(/>/g,\'&gt;\');}\nfunction decorate(line){\n  let h = esc(line);\n  h = h.replace(/\\[ORCHESTRATOR\\]/g,\'<span class="tok-orch">[ORCHESTRATOR]</span>\');\n  h = h.replace(/\\[TOOL [^\\]]+\\]/g,function(m){return \'<span class="tok-tool">\'+m+\'</span>\';});\n  h = h.replace(/\\[MEMORY\\]/g,\'<span class="tok-mem">[MEMORY]</span>\');\n  h = h.replace(/GUARDRAIL/g,\'<span class="tok-guard">GUARDRAIL</span>\');\n  return h;\n}\nfunction renderOut(text){\n  document.getElementById(\'rawtext\').textContent = text;\n  const lines = text.split(\'\\n\');\n  let html = \'\';\n  for(const line of lines){\n    let matched = null;\n    for(const s of SECTIONS){ if(line.indexOf(s.m) !== -1){ matched = s; break; } }\n    if(matched){\n      html += \'<div class="sechead">\'+decorate(line)+\'</div>\'+\n              \'<div class="seccap">\'+matched.c+\'</div>\';\n      continue;\n    }\n    html += decorate(line) + \'\\n\';\n  }\n  document.getElementById(\'outtext\').innerHTML = html;\n  document.getElementById(\'output\').classList.add(\'show\');\n  document.getElementById(\'output\').scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\nfunction showTakeaways(){\n  const t = document.getElementById(\'takeaways\');\n  t.style.display=\'block\'; t.classList.add(\'show\');\n  t.scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\ndocument.getElementById(\'run\').addEventListener(\'click\',function(){\n  const btn=this, spin=document.getElementById(\'spin\');\n  btn.disabled=true; spin.classList.add(\'show\');\n  fetch(\'/api/run\').then(r=>r.json()).then(j=>{\n    spin.classList.remove(\'show\'); btn.disabled=false;\n    renderOut(j.output);\n    if(typeof loadDecisionTable===\'function\') loadDecisionTable();\n    showTakeaways();\n  }).catch(e=>{spin.classList.remove(\'show\');btn.disabled=false;alert(\'Run failed: \'+e);});\n});\n\nfunction collectFilter(){\n  return {min_age:document.getElementById(\'f_age\').value,\n          min_cond:document.getElementById(\'f_cond\').value,\n          min_days:document.getElementById(\'f_pcp\').value,\n          transport:document.getElementById(\'f_trans\').value};\n}\nfunction decTable(rows){\n  if(!rows.length) return \'\';\n  let h=\'<table class="dec"><thead><tr><th>Member</th><th>Why they were flagged</th><th>Recommendation</th><th>Reason</th></tr></thead><tbody>\';\n  for(const r of rows){\n    const cls = r.rec===\'VISIT\' ? \'v\' : \'s\';\n    h+=\'<tr><td>\'+esc(r.member)+\'</td><td>\'+esc(r.why)+\'</td>\'+\n       \'<td><span class="pill \'+cls+\'">\'+r.rec+\'</span></td><td>\'+esc(r.reason)+\'</td></tr>\';\n  }\n  return h+\'</tbody></table>\';\n}\nfunction emptyHelpHtml(eh){\n  let h=\'<div class="emptyhelp"><p><b>0 members</b> matched all of your filters. \'\n    +\'Tightest filter: <b>\'+esc(eh.tightest)+\'</b> — only \'+eh.tightest_count+\' clear it alone.</p>\';\n  h+=\'<p class="hint">Each filter on its own: \'\n    +Object.keys(eh.per_filter).map(function(k){return esc(k)+\': \'+eh.per_filter[k];}).join(\' / \')+\'</p>\';\n  if(eh.relax && eh.relax.length){\n    h+=\'<p>Try loosening one filter:</p><div class="btnrow">\';\n    eh.relax.forEach(function(o){\n      h+=\'<button class="ghost" data-field="\'+o.field+\'" data-value="\'+esc(o.value)+\'">\'\n        +esc(o.desc)+\' → \'+o.count+\' match\'+(o.count===1?\'\':\'es\')+\'</button>\';\n    });\n    h+=\'</div>\';\n  } else {\n    h+=\'<p class="hint">Even dropping one filter finds nobody — reset to the defaults (75 / 2 / 180 / no preference).</p>\';\n  }\n  return h+\'</div>\';\n}\nfunction wireRelaxButtons(){\n  const btns=document.querySelectorAll(\'#filterNote [data-field]\');\n  for(const b of btns){\n    b.addEventListener(\'click\',function(){\n      const f=document.getElementById(b.getAttribute(\'data-field\'));\n      if(f){ f.value=b.getAttribute(\'data-value\'); }\n      document.getElementById(\'filterRun\').click();\n    });\n  }\n}\ndocument.getElementById(\'filterRun\').addEventListener(\'click\',function(){\n  const spin=document.getElementById(\'fspin\'); spin.classList.add(\'show\');\n  fetch(\'/api/filter\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n    body:JSON.stringify(collectFilter())})\n  .then(r=>r.json()).then(j=>{\n    spin.classList.remove(\'show\');\n    let html=\'<p class="hint">\'+esc(j.note)+\'</p>\';\n    if(j.extra && j.extra.empty_help){ html+=emptyHelpHtml(j.extra.empty_help); }\n    document.getElementById(\'filterNote\').innerHTML=html;\n    wireRelaxButtons();\n    const sec=document.getElementById(\'dectable\'); sec.style.display=\'block\';\n    document.getElementById(\'tableModeLabel\').innerHTML=\'<b>Your filtered results</b> — the agent recommends, <b>you</b> approve.\';\n    document.getElementById(\'decisionTable\').innerHTML = j.rows.length ? decTable(j.rows)\n      : \'<p class="hint">Nothing to show yet — loosen a filter above and try again.</p>\';\n    sec.scrollIntoView({behavior:\'smooth\',block:\'start\'});\n  })\n  .catch(e=>{spin.classList.remove(\'show\');alert(\'Filter failed: \'+e);});\n});\nfunction loadDecisionTable(){\n  fetch(\'/api/table\').then(r=>r.json()).then(j=>{\n    document.getElementById(\'dectable\').style.display=\'block\';\n    document.getElementById(\'tableModeLabel\').innerHTML=\'<b>From the guided demo run (canned data)</b> — the agent recommends, <b>you</b> approve.\';\n    document.getElementById(\'decisionTable\').innerHTML=decTable(j.rows);\n  });\n}\n\nfunction wireCustom(){\n  const b=document.getElementById(\'customRun\');\n  if(!b) return;\n  b.addEventListener(\'click\',function(){\n    const spin=document.getElementById(\'cspin\');\n    b.disabled=true; spin.classList.add(\'show\');\n    fetch(\'/api/custom\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n      body:JSON.stringify(collectCustom())})\n    .then(r=>r.json()).then(j=>{\n      spin.classList.remove(\'show\'); b.disabled=false;\n      if(j.error){alert(j.error);return;}\n      renderOut(j.output); showTakeaways();\n    }).catch(e=>{spin.classList.remove(\'show\');b.disabled=false;alert(\'Run failed: \'+e);});\n  });\n}\n</script>\n</body>\n</html>\n'

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "WorkshopUI/1.0"

    def _send(self, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        self._send(json.dumps(obj), "application/json; charset=utf-8")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _serve_asset(self, path):
        safe = (HERE / path.lstrip("/")).resolve()
        try:
            safe.relative_to(HERE / "assets")
        except ValueError:
            return self.send_error(403, "forbidden")
        if not safe.is_file():
            return self.send_error(404, "not found")
        ctype, _ = mimetypes.guess_type(str(safe))
        data = safe.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self._send(PAGE)
        elif path == "/api/run":
            self._json({"output": _capture_canned()})
        elif path.startswith("/assets/"):
            self._serve_asset(path)

        elif path == "/api/table":
            rows = hhv_decision_table()
            self._json({"rows": rows})
        else:
            self.send_error(404, "not found")

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/custom":
            params = self._read_json()
            self._json(_capture_custom(run_custom, params))

        elif path == "/api/filter":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            params = json.loads(raw.decode("utf-8") or "{}")
            rows, note, extra = hhv_filter(params)
            self._json({"rows": rows, "note": note, "extra": extra})
        else:
            self.send_error(404, "not found")

    def log_message(self, fmt, *args):
        sys.stderr.write("ui: " + (fmt % args) + "\n")


def main():
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print("HHV Copilot demo UI -> http://localhost:8002")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
