#!/usr/bin/env python3
"""VELDO Run Lens local status server: serve the R3 read model live in a browser.

This is the thin read surface of the Run Lens (PLAN-0005 F3, R4). It is a small
stdlib http server and NOTHING more: no framework, no database, no message bus,
no daemon, and no app state beyond a config dict. It serves exactly the model
the R3 reader assembles - the same model veldo status --json prints - so there is
ONE projection, never a second one that could drift:

  GET /status   runstatus.status() as JSON (identical to veldo status --json)
  GET /          a small self-contained HTML+JS page (inline CSS and JS, no
                 external asset or CDN) that renders /status and refreshes,
                 preferring the /events live stream and falling back to polling
  GET /events    a Server-Sent-Events stream that pushes the model on an interval

Two properties are load-bearing and are asserted in the gate selftest:

  LOCALHOST ONLY. The server binds 127.0.0.1, never 0.0.0.0, so it is not
  reachable off the machine. There is therefore no remote surface to protect,
  and (with no write path, below) no authentication is needed. If a future
  control endpoint is ever added it MUST require an ephemeral token; the read
  endpoints stay localhost-only.

  READ-ONLY. Every endpoint reads through runstatus (git, the event stream, the
  run registry) and writes NOTHING - not to the registry, not to the events
  stream, not to the repo. Only GET is implemented; any other method gets the
  stdlib 501. The model already excludes secrets, so nothing sensitive is served.

The roots (root, runs_root, events_path) are overridable so the server's control
logic is gate-tested over a temporary runs root and a real ephemeral 127.0.0.1
port with no external service, and shut down cleanly.

  python3 .veldo/status_server.py [--port N]     start the server (0 picks a port)
  veldo status --serve [--port N]                the CLI front door (runstatus)
"""
import argparse
import importlib.util
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Loopback only. Never 0.0.0.0: the lens is a personal read surface for a running
# build on this machine, not a networked service.
HOST = "127.0.0.1"

# Browser refresh cadence (poll fallback) and SSE push interval, in seconds.
DEFAULT_REFRESH_SECONDS = 3

_MODCACHE = {}


def _load(name, rel):
    """Load a sibling .veldo module by path, matching the codebase convention."""
    if name not in _MODCACHE:
        spec = importlib.util.spec_from_file_location(name, ROOT / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODCACHE[name] = mod
    return _MODCACHE[name]


def build_model(config):
    """Assemble the read model - the SAME projection veldo status --json prints.

    There is no second model here: the server calls runstatus.status() with the
    caller's roots and serves exactly what it returns, so the browser view and
    the CLI can never disagree."""
    RS = _load("veldo_status_server_runstatus", ".veldo/runstatus.py")
    return RS.status(
        root=config.get("root"),
        runs_root=config.get("runs_root"),
        events_path=config.get("events_path"),
    )


# A self-contained page: inline CSS and JS, no external asset, no CDN, no font.
# The only network calls it makes are same-origin GET /events and GET /status.
_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VELDO Run Lens</title>
<style>
body{font:14px/1.5 ui-monospace,Menlo,Consolas,monospace;margin:0;padding:1.5rem;
  background:#0f1115;color:#d7dbe0;}
h1{font-size:1.1rem;margin:0 0 .25rem;color:#8fb3ff;}
.sub{color:#7c8695;margin-bottom:1.25rem;font-size:.85rem;}
.card{background:#171a21;border:1px solid #262b36;border-radius:8px;
  padding:.85rem 1rem;margin-bottom:1rem;}
.card h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;
  color:#7c8695;margin:0 0 .6rem;}
.run{display:flex;flex-wrap:wrap;gap:.5rem 1rem;padding:.5rem 0;
  border-top:1px solid #22262f;}
.run:first-of-type{border-top:0;}
.tag{border-radius:4px;padding:.05rem .45rem;font-size:.78rem;font-weight:600;}
.active{background:#123524;color:#6ee7a8;}
.blocked{background:#3a2412;color:#f5b971;}
.stale{background:#2a2d34;color:#9aa4b2;}
.done{background:#1b2438;color:#8fb3ff;}
.fired{background:#3a1212;color:#f59a9a;}
.k{color:#7c8695;}
.q{color:#f5b971;flex-basis:100%;}
.muted{color:#7c8695;}
table{border-collapse:collapse;width:100%;font-size:.82rem;}
td,th{text-align:left;padding:.2rem .5rem;border-top:1px solid #22262f;}
th{color:#7c8695;font-weight:600;}
.empty{color:#7c8695;font-style:italic;}
#conn{font-size:.75rem;color:#7c8695;}
</style>
</head><body>
<h1>VELDO Run Lens</h1>
<div class="sub" id="head">connecting...</div>
<div class="card"><h2>Live runs</h2><div id="runs"><span class="empty">loading</span></div></div>
<div class="card"><h2>Burn-down</h2><div id="burndown"><span class="empty">loading</span></div></div>
<div class="card"><h2>Tripwires</h2><div id="tripwires"><span class="empty">loading</span></div></div>
<div class="card"><h2>Recent events</h2><div id="events"><span class="empty">loading</span></div></div>
<div id="conn"></div>
<script>
var REFRESH_MS = __REFRESH_MS__;
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];});}
function num(v){return v==null?'unknown':esc(v);}
function render(m){
  var repo=m.repo||{};
  document.getElementById('head').textContent=
    (repo.branch||'?')+' @ '+String(repo.head||'?').slice(0,12)+
    '  ('+(m.runs||[]).length+' run(s))  '+(m.at||'');
  var runs=m.runs||[], rh='';
  if(!runs.length){rh='<span class="empty">no live runs</span>';}
  for(var i=0;i<runs.length;i++){var r=runs[i];
    var hb=r.heartbeat_age_seconds; hb=(hb==null)?'unknown':(hb+'s');
    rh+='<div class="run"><span class="tag '+esc(r.classification||'')+'">'+
      esc(r.classification||'?')+'</span>'+
      '<span><span class="k">spec</span> '+esc(r.spec_id||'?')+'</span>'+
      '<span><span class="k">phase</span> '+esc(r.phase||'-')+'</span>'+
      '<span><span class="k">hb</span> '+hb+'</span>'+
      '<span><span class="k">min</span> '+num(r.human_minutes)+'</span>'+
      '<span><span class="k">tok</span> '+num(r.tokens)+'</span>';
    if(r.classification==='blocked'){
      var be=r.blocked_elapsed_seconds; be=(be==null)?'unknown':(be+'s');
      rh+='<span class="q">blocked '+be+': '+esc(r.question||'(no question)')+'</span>';}
    rh+='</div>';}
  document.getElementById('runs').innerHTML=rh;
  var bd=m.burndown||[], bh='';
  if(!bd.length){bh='<span class="empty">no plans</span>';}
  else{bh='<table><tr><th>Plan</th><th>Status</th><th>Shipped</th><th>Frontier</th></tr>';
    for(var j=0;j<bd.length;j++){var p=bd[j];
      bh+='<tr><td>'+esc(p.id)+'</td><td>'+esc(p.status)+'</td><td>'+
        esc(p.shipped)+'/'+esc(p.total)+'</td><td class="muted">'+
        esc((p.frontier||[]).join(', ')||'none')+'</td></tr>';}
    bh+='</table>';}
  document.getElementById('burndown').innerHTML=bh;
  var tw=m.tripwires||{}, fired=tw.fired||[], warns=tw.warnings||[], th='';
  if(!fired.length&&!warns.length){th='<span class="empty">no fired tripwires</span>';}
  else{
    for(var t=0;t<fired.length;t++){var f=fired[t];
      th+='<div class="run"><span class="tag fired">FIRED</span>'+
        '<span><span class="k">decision</span> '+esc(f.decision||'?')+'</span>'+
        '<span><span class="k">assumption</span> '+esc(f.assumption||'?')+'</span>'+
        '<span class="q">'+esc(f.detail||'')+'</span></div>';}
    for(var u=0;u<warns.length;u++){var w=warns[u];
      th+='<div class="run"><span class="tag stale">'+esc(w.state||'warn')+'</span>'+
        '<span><span class="k">decision</span> '+esc(w.decision||'?')+'</span>'+
        '<span><span class="k">assumption</span> '+esc(w.assumption||'?')+'</span>'+
        '<span class="muted">'+esc(w.detail||'')+'</span></div>';}}
  document.getElementById('tripwires').innerHTML=th;
  var ev=m.events_tail||[], eh='';
  if(!ev.length){eh='<span class="empty">no events</span>';}
  else{eh='<table>';
    for(var k=ev.length-1;k>=0;k--){var e=ev[k];
      eh+='<tr><td class="muted">'+esc(e.at||'')+'</td><td>'+esc(e.type||'?')+
        '</td><td>'+esc(e.spec_id||e.correlation_id||'')+'</td></tr>';}
    eh+='</table>';}
  document.getElementById('events').innerHTML=eh;
}
function conn(t){document.getElementById('conn').textContent=t;}
function poll(){fetch('/status').then(function(r){return r.json();})
  .then(function(m){render(m);conn('polling every '+(REFRESH_MS/1000)+'s');})
  .catch(function(){conn('poll failed; retrying');});}
var polling=false;
function startPolling(){if(polling)return;polling=true;setInterval(poll,REFRESH_MS);poll();}
try{
  var es=new EventSource('/events');
  es.onmessage=function(e){try{render(JSON.parse(e.data));conn('live (SSE)');}catch(x){}};
  es.onerror=function(){if(!polling){es.close();startPolling();}};
}catch(x){startPolling();}
poll();
</script>
</body></html>
"""


def page(config):
    ms = int(config.get("refresh_seconds", DEFAULT_REFRESH_SECONDS)) * 1000
    return _PAGE.replace("__REFRESH_MS__", str(ms))


class _Handler(BaseHTTPRequestHandler):
    """Read-only request handler. Only GET is implemented; POST/PUT/DELETE fall
    through to the stdlib 501, so there is no write surface at all."""

    server_version = "VeldoRunLens/1"

    def log_message(self, *args):
        # A read-only lens does not spam the console; the caller sees the banner.
        pass

    def _send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        cfg = self.server.veldo_config
        if path == "/status":
            self._send(200, json.dumps(build_model(cfg), indent=2),
                       "application/json; charset=utf-8")
        elif path == "/":
            self._send(200, page(cfg), "text/html; charset=utf-8")
        elif path == "/events":
            self._sse(cfg)
        else:
            self._send(404, json.dumps({"error": "not found", "path": self.path}),
                       "application/json; charset=utf-8")

    def _sse(self, cfg):
        stop = getattr(self.server, "stop_event", None)
        interval = cfg.get("refresh_seconds", DEFAULT_REFRESH_SECONDS)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            while stop is None or not stop.is_set():
                payload = json.dumps(build_model(cfg))
                self.wfile.write(("data: " + payload + "\n\n").encode("utf-8"))
                self.wfile.flush()
                # Interruptible wait so the stream ends promptly on shutdown.
                if stop is not None:
                    if stop.wait(interval):
                        break
                else:
                    time.sleep(interval)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return


def make_server(port=0, host=HOST, root=None, runs_root=None, events_path=None,
                refresh_seconds=DEFAULT_REFRESH_SECONDS):
    """Build (do not start) the localhost status server. host defaults to
    127.0.0.1 and is not meant to be widened; a caller that passes 0.0.0.0 is
    caught by the gate selftest, which asserts the bound host is loopback."""
    httpd = ThreadingHTTPServer((host, port), _Handler)
    httpd.daemon_threads = True
    httpd.stop_event = threading.Event()
    httpd.veldo_config = {
        "root": str(root) if root else None,
        "runs_root": runs_root,
        "events_path": str(events_path) if events_path else None,
        "refresh_seconds": refresh_seconds,
    }
    return httpd


def serve(port=0, host=HOST, root=None, runs_root=None, events_path=None,
          refresh_seconds=DEFAULT_REFRESH_SECONDS):
    httpd = make_server(port=port, host=host, root=root, runs_root=runs_root,
                        events_path=events_path, refresh_seconds=refresh_seconds)
    bhost, bport = httpd.server_address[0], httpd.server_address[1]
    print("VELDO Run Lens on http://%s:%d/  (read-only, localhost only)" % (bhost, bport))
    print("  GET /        live browser view")
    print("  GET /status  the read model as JSON (same as veldo status --json)")
    print("  GET /events  server-sent live updates")
    print("Ctrl-C to stop.")
    try:
        httpd.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.stop_event.set()
        httpd.server_close()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="VELDO Run Lens read-only local status server (localhost only).")
    ap.add_argument("--port", type=int, default=0,
                    help="TCP port on 127.0.0.1; 0 (default) picks a free port")
    ap.add_argument("--refresh", type=int, default=DEFAULT_REFRESH_SECONDS,
                    help="browser refresh / SSE push interval in seconds")
    args = ap.parse_args(argv)
    return serve(port=args.port, refresh_seconds=args.refresh)


if __name__ == "__main__":
    sys.exit(main())
