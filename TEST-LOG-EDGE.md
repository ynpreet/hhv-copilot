# Edge-Case Test Log — HHV Copilot (web UI + registry)

Date: 2026-10-10. Deterministic: same inputs -> same outputs (seeded RNG only).

## Data expansion (variety, stat-neutral)
- demo.py: new `apply_variety_swap()` pass using a SEPARATE seeded stream (SEED+1).
  35% of members get one condition label swapped from 6 new conditions
  (Osteoporosis, Chronic Pain, Anxiety, Sleep Apnea, GERD, Anemia);
  45% get a new first/last name from 12+12 new senior-appropriate names;
  25% get a screening label swapped from 2 new screenings.
- Verified: every baked stat identical before/after swap (age75/85, cond2/3/4,
  max_cond=4, days180/365, max_days, max_age, ride counts; identified count 265).
- Featured deep-dive member (Margaret Ellis, HHV-M0042) explicitly excluded from swaps.
- app.py `_hhv_data()` now uses the same pipeline as the canned demo
  (generate -> featured override -> variety swap); previously it skipped the override,
  so the web UI and the canned demo disagreed on 3 members' fields.
- Baked UI hints reconciled to the true registry: 85+ 338->337, 365+ days 321->320,
  ride need 273->274 (these shifted because the override is now applied, not the swap).
- Max conditions bound stays 4; filter maxes and all hints consistent.
- Canned `demo.py` re-run: completes, 265 identified, 8 high utilizers excluded — beats intact.

## Fixes applied during hardening
1. `_read_json`: malformed JSON -> {} instead of a dead connection.
2. `/api/filter`: wrapped end-to-end; any failure returns HTTP 200 with an honest
   "could not be applied" note instead of dying.
3. `hhv_filter`: non-dict params (JSON string/null/number/array) coerced to {}.
4. Removed dead `/api/custom` endpoint (referenced a non-existent `run_custom` ->
   NameError -> dead connection on every POST). Now 404s honestly; the real
   personalized path is `/api/filter`.

## 14-case filter battery (function level) — ALL PASS
- age 0/200/-5, cond 5/huge, days huge/negative, non-numeric strings, None values,
  "75.9" floats, whitespace-padded, empty dict, non-dict (str/None/int/list):
  every case returns JSON-serializable rows/note/extra, never raises.

## HTTP battery (live server, port 8002) — ALL PASS
- /api/filter: malformed JSON / empty body -> HTTP 200, no traceback.
- Removed /api/custom: malformed / empty / 10KB junk -> honest 404, connection stays alive.
- 24 concurrent requests -> all 200, no tracebacks.
