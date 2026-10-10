# Test Log — 10x Reliability Gate

Date: 2026-10-10
Machine: Linux VM, Python 3.12.3, stdlib only

## Result: 10/10 PASSED, byte-identical output on every run

Method: `python3 demo.py` executed 10 consecutive times; each run's stdout
was captured and hashed (SHA-256). All 10 runs exited 0; all 10 hashes
matched (1 unique hash), confirming the demo is fully deterministic and
stage-safe.

Unique output hash (all runs):
`a1b0b4a9b50c212557cfba570ab9cd56c9700e6e54a2c2a2d59983e57c69a8e1`

| Run | Exit code | SHA-256 (stdout) | Match |
|-----|-----------|------------------|-------|
| 1 | 0 | a1b0b4a9…0171d1b5 | ✅ |
| 2 | 0 | a1b0b4a9…0171d1b5 | ✅ |
| 3 | 0 | a1b0b4a9…0171d1b5 | ✅ |
| 4 | 0 | a1b0b4a9…0171d1b5 | ✅ |
| 5 | 0 | a1b0b4a9…0171d1b5 | ✅ |
| 6 | 0 | a1b0b4a9…0171d1b5 | ✅ |
| 7 | 0 | a1b0b4a9…0171d1b5 | ✅ |
| 8 | 0 | a1b0b4a9…0171d1b5 | ✅ |
| 9 | 0 | a1b0b4a9…0171d1b5 | ✅ |
| 10 | 0 | a1b0b4a9…0171d1b5 | ✅ |

Determinism sources: fixed random seed (`SEED = 20261010`) for the synthetic
registry, fixed "today" (`DEMO_TODAY = 2026-10-10`, never `datetime.now()`),
explicit sort keys on every ranking, no wall-clock or hash-randomization
dependence anywhere in the output path.

The demo requires no network, no API keys, and no pip installs
(`requirements.txt` is stdlib-only by design). Typical runtime: <0.1s.

---

## Web UI test log

Date: 2026-10-10
Machine: Linux VM, Python 3.12.3, stdlib only (`app.py` — `http.server`)
Scope: 12 test rounds of the localhost web UI.

Each round:
- (a) `python3 demo.py` → exit 0 (demo behavior unchanged; `app.py` only
  runs it as a subprocess)
- (b) start `python3 app.py` on port 8002 (bind 127.0.0.1), then
  `curl http://localhost:8002/` → 200 (serves the single-page UI) and
  `curl http://localhost:8002/api/run` → 200 with
  `{"ok": true, "output": "..."}` where `output` contains the stable
  demo.py markers `HHV COPILOT`, `EXPECTED_PROCESSING_DELAY`, and
  `Margaret Ellis`; kill the server.

| Rounds | Result |
|--------|--------|
| 1–12 | 12/12 PASSED ✅ |

Findings fixed during testing:
1. Stdout block-buffering: the `Open in Chrome: http://localhost:8002`
   startup line was not visible immediately when stdout was redirected —
   fixed with `flush=True` on all startup prints.
2. Round 12 initially ran while a prior test server was still alive:
   `app.py` correctly refused to start and printed a clear error
   (`Port 8002 on 127.0.0.1 is already in use.` + remediation hints),
   confirming the port-conflict path. Round 12 re-ran clean after the
   stale server exited.

Reproduce:

```bash
cd ~/workspace/agentic-ai-workshop/hhv-copilot
python3 app.py          # then open http://localhost:8002 in Chrome
```
