#!/usr/bin/env python3
"""HHV Copilot — localhost web UI for the live demo.

Stdlib only (http.server). Run:

    python3 app.py

then open http://localhost:8002 in Google Chrome.

Endpoints:
    GET /         -> the single-page demo UI
    GET /api/run  -> runs `python3 demo.py` as a subprocess, returns
                     {"ok": true, "output": "..."} as JSON

demo.py is never modified or imported; it is only executed in a
subprocess, exactly as `python3 demo.py` on the command line.
"""

import http.server
import json
import socket
import subprocess
import sys
import threading
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8002
HERE = Path(__file__).resolve().parent
DEMO_PY = HERE / "demo.py"

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HHV Copilot — Live Demo</title>
<style>
  :root{
    --bg:#0e1420; --panel:#16202f; --panel2:#1b283c; --ink:#e8eef6;
    --muted:#9fb0c3; --accent:#4fc3f7; --accent2:#81c784; --warn:#ffb74d;
    --danger:#e57373; --line:#2a3b52;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
    Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink)}
  header{background:linear-gradient(135deg,#0b2a3a,#123f63);padding:26px 32px;
    border-bottom:1px solid var(--line)}
  header h1{margin:0 0 6px;font-size:24px}
  header p{margin:0;color:var(--muted);font-size:14px;max-width:760px}
  .tag{display:inline-block;margin-top:10px;font-size:11px;letter-spacing:.08em;
    text-transform:uppercase;color:#0b2a3a;background:var(--accent2);
    padding:3px 10px;border-radius:999px;font-weight:700}
  main{padding:24px 32px;max-width:1080px;margin:0 auto}
  .controls{display:flex;gap:12px;align-items:center;margin-bottom:18px;
    flex-wrap:wrap}
  button#run{background:var(--accent);border:0;color:#062a3a;font-weight:700;
    font-size:15px;padding:12px 26px;border-radius:8px;cursor:pointer}
  button#run:disabled{opacity:.45;cursor:default}
  .hint{color:var(--muted);font-size:13px}
  .spinner{display:none;align-items:center;gap:10px;color:var(--muted);
    font-size:14px}
  .spinner.show{display:flex}
  .dot{width:12px;height:12px;border-radius:50%;background:var(--accent);
    animation:pulse 1s infinite ease-in-out}
  @keyframes pulse{0%,100%{transform:scale(.6);opacity:.5}
    50%{transform:scale(1.2);opacity:1}}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:18px}
  @media(max-width:900px){.grid{grid-template-columns:1fr}}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
    overflow:hidden}
  .card h2{margin:0;padding:12px 16px;font-size:13px;letter-spacing:.06em;
    text-transform:uppercase;color:var(--accent);background:var(--panel2);
    border-bottom:1px solid var(--line)}
  .card .body{max-height:520px;overflow:auto;padding:12px 16px;
    font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    font-size:12.5px;line-height:1.55;white-space:pre-wrap;word-wrap:break-word}
  .plan{background:rgba(79,195,247,.10);border:1px solid var(--accent);
    border-radius:8px;padding:12px;margin-bottom:12px}
  .plan .label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;
    color:var(--accent);font-weight:700;margin-bottom:6px}
  .tok-orch{color:var(--accent);font-weight:700}
  .tok-tool{color:var(--accent2);font-weight:700}
  .tok-guard{color:var(--warn);font-weight:700}
  .empty{color:var(--muted);font-family:-apple-system,BlinkMacSystemFont,
    "Segoe UI",sans-serif}
  footer{padding:16px 32px;color:var(--muted);font-size:12px;text-align:center}
  .err{color:var(--danger);font-weight:700}
</style>
</head>
<body>
<header>
  <h1>HHV Copilot</h1>
  <p>An agentic AI system for Medicare Advantage in-home assessments — one
  orchestrator, specialized tools, deterministic guardrails. All 1,000 members
  are synthetic teaching data; no network, no API keys.</p>
  <span class="tag">Demo 5 of 5 &middot; Agentic AI Workshop</span>
</header>
<main>
  <div class="controls">
    <button id="run">▶ Run live demo</button>
    <div class="spinner" id="spinner"><div class="dot"></div>
      <span>Agent is running the 7-step lifecycle…</span></div>
    <span class="hint" id="status">Runs <code>python3 demo.py</code> on this machine and streams its trace.</span>
  </div>
  <div class="grid">
    <div class="card">
      <h2>Agent trace — plan &amp; tool calls</h2>
      <div class="body" id="trace"><span class="empty">Press “Run live demo” to start the agent.</span></div>
    </div>
    <div class="card">
      <h2>Results — dashboard &amp; self-eval</h2>
      <div class="body" id="results"><span class="empty">Results appear here after the run.</span></div>
    </div>
  </div>
</main>
<footer>HHV Copilot · localhost demo · educational — synthetic data only</footer>
<script>
(function(){
  var runBtn = document.getElementById('run');
  var spinner = document.getElementById('spinner');
  var status  = document.getElementById('status');
  var traceEl = document.getElementById('trace');
  var resEl   = document.getElementById('results');

  function esc(s){
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;')
            .replace(/>/g,'&gt;');
  }
  function highlight(line){
    var h = esc(line);
    h = h.replace(/\[ORCHESTRATOR\]/g,'<span class="tok-orch">[ORCHESTRATOR]</span>');
    h = h.replace(/\[TOOL\]/g,'<span class="tok-tool">[TOOL]</span>');
    h = h.replace(/GUARDRAIL|guardrail/gi,function(m){
      return '<span class="tok-guard">'+esc(m)+'</span>';});
    return h;
  }
  function splitOutput(text){
    // Split the demo output into a highlighted plan block and the rest.
    var planStart = text.indexOf('[ORCHESTRATOR] PLAN');
    var execStart = text.indexOf('[ORCHESTRATOR] Executing the plan.');
    if(planStart !== -1 && execStart !== -1 && execStart > planStart){
      return {plan: text.slice(planStart, execStart).trim(),
              rest: text.slice(execStart).trim()};
    }
    return {plan: '', rest: text};
  }
  runBtn.addEventListener('click', function(){
    runBtn.disabled = true;
    spinner.classList.add('show');
    status.textContent = 'Running…';
    var started = Date.now();
    fetch('/api/run')
      .then(function(r){ return r.json(); })
      .then(function(data){
        var secs = ((Date.now()-started)/1000).toFixed(1);
        if(!data.ok){
          traceEl.innerHTML = '<span class="err">Run failed:</span> '
            + esc(data.error || 'unknown error');
          resEl.innerHTML = '<span class="empty">—</span>';
        } else {
          var parts = splitOutput(data.output || '');
          var html = '';
          if(parts.plan){
            html += '<div class="plan"><div class="label">Agent plan</div>'
              + parts.plan.split('\n').map(highlight).join('\n') + '</div>';
          }
          traceEl.innerHTML = html
            + parts.rest.split('\n').map(highlight).join('\n');
          resEl.innerHTML = parts.rest.split('\n').map(highlight).join('\n');
          status.textContent = 'Finished in ' + secs + 's — exit 0.';
        }
      })
      .catch(function(err){
        traceEl.innerHTML = '<span class="err">Request failed:</span> '
          + esc(String(err));
      })
      .finally(function(){
        runBtn.disabled = false;
        spinner.classList.remove('show');
      });
  });
})();
</script>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "HHVCopilotUI/1.0"

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write("127.0.0.1 - %s\n" % (fmt % args))

    def _send(self, status, body, content_type):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._send(200, PAGE, "text/html")
        elif self.path == "/api/run":
            self.handle_api_run()
        else:
            self._send(404, '{"ok": false, "error": "not found"}',
                        "application/json")

    def handle_api_run(self):
        if not DEMO_PY.exists():
            self._send(500, json.dumps(
                {"ok": False, "error": "demo.py not found next to app.py"}),
                "application/json")
            return
        try:
            proc = subprocess.run(
                [sys.executable, str(DEMO_PY)],
                cwd=str(HERE),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            self._send(504, json.dumps(
                {"ok": False, "error": "demo.py timed out after 60s"}),
                "application/json")
            return
        if proc.returncode != 0:
            self._send(500, json.dumps({
                "ok": False,
                "error": "demo.py exited with code %d: %s"
                % (proc.returncode, proc.stderr[-2000:]),
            }), "application/json")
            return
        self._send(200, json.dumps({"ok": True, "output": proc.stdout}),
                   "application/json")


def main():
    try:
        server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        print("ERROR: could not start HHV Copilot web UI.", file=sys.stderr)
        print("Port %d on %s is already in use." % (PORT, HOST),
              file=sys.stderr)
        print("Stop the other server first (e.g. `pkill -f 'app.py'`) or "
              "find it with `lsof -i :%d`." % PORT, file=sys.stderr)
        print("Original error: %s" % exc, file=sys.stderr)
        sys.exit(1)
    print("=" * 60, flush=True)
    print("HHV Copilot — live demo web UI", flush=True)
    print("=" * 60, flush=True)
    print("Serving demo folder: %s" % HERE, flush=True)
    print("Open in Chrome: http://localhost:%d" % PORT, flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    print("=" * 60, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
