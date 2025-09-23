# main.py
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine, get_db
from .seed import seed
from .routers import items, qa

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Vishal's Fast API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:8000"] if you want to scope it
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/init")
def init(db: Session = Depends(get_db)):
    seed(db, employees=60, days=45)
    return {"ok": True, "msg": "Seeded demo data"}

app.include_router(qa.router)
app.include_router(items.router)

@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}

@app.get("/debug/sse", response_class=HTMLResponse)
def sse_debug_page():
    return """
<!doctype html>
<meta charset="utf-8" />
<title>SSE Tester</title>
<style>
  :root { font-family: ui-sans-serif, system-ui, Segoe UI, Roboto, Helvetica, Arial; }
  body { margin: 24px; }
  h2 { margin: 18px 0 6px; }
  fieldset { border: 1px solid #ddd; padding: 12px; border-radius: 8px; margin-bottom: 18px; }
  label { display: inline-block; min-width: 72px; }
  input { width: 90px; padding: 4px 6px; }
  button { padding: 6px 10px; margin-right: 8px; cursor: pointer; }
  .log { border: 1px solid #e2e2e2; border-radius: 8px; padding: 10px; height: 280px; overflow: auto; background: #fafafa; }
  .line { white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; margin: 2px 0; }
  .ok { color: #0a7; }
  .err { color: #c00; }
</style>

<h1>FastAPI SSE Tester</h1>

<fieldset>
  <legend>/items/_stream (progress)</legend>
  <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
    <label>Steps</label><input id="steps" type="number" value="12" min="1" />
    <label>Delay</label><input id="delay" type="number" value="0.3" step="0.05" />
    <button id="startProgress">Start</button>
    <button id="stopProgress">Stop</button>
  </div>
  <div class="log" id="logProgress"></div>
</fieldset>

<fieldset>
  <legend>/items/stream-ping (heartbeat + count)</legend>
  <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
    <label>Interval</label><input id="interval" type="number" value="2" step="0.1" />
    <button id="startPing">Start</button>
    <button id="stopPing">Stop</button>
  </div>
  <div class="log" id="logPing"></div>
</fieldset>

<button onclick="window.print()">🖨️ Print page</button>

<script>
  const BASE = location.origin; // same origin as FastAPI

  let esProgress = null;
  let esPing = null;

  // helpers
  function line(el, text, cls="") {
    const div = document.createElement("div");
    div.className = "line " + cls;
    div.textContent = text;
    el.appendChild(div);
    el.scrollTop = el.scrollHeight;
  }
  function safeParse(json) {
    try { return JSON.parse(json); } catch { return json; }
  }

  // --- PROGRESS STREAM ---
  document.addEventListener("click", (e) => {
    if (e.target.id === "startProgress") {
      const steps = Number(document.getElementById("steps").value || 12);
      const delay = Number(document.getElementById("delay").value || 0.3);
      const log = document.getElementById("logProgress");
      log.innerHTML = "";
      if (esProgress) esProgress.close();

      const url = `${BASE}/items/_stream?steps=${encodeURIComponent(steps)}&delay=${encodeURIComponent(delay)}`;
      line(log, `Connecting: ${url}`, "ok");
      const es = new EventSource(url);
      esProgress = es;

      es.addEventListener("hello", (ev) => line(log, `hello: ${ev.data}`, "ok"));
      es.addEventListener("progress", (ev) => {
        const data = safeParse(ev.data);
        line(log, `progress: ${typeof data === 'string' ? data : JSON.stringify(data)}`);
        if (typeof data === 'object' && data.progress === 100) {
          line(log, "closing (100%)", "ok");
          es.close();
        }
      });
      es.addEventListener("done", (ev) => line(log, `done: ${ev.data}`, "ok"));
      es.onmessage = (ev) => line(log, `message: ${ev.data}`);
      es.onerror = () => line(log, `error (network/disconnected)`, "err");
    }
    if (e.target.id === "stopProgress") {
      const log = document.getElementById("logProgress");
      if (esProgress) {
        esProgress.close();
        esProgress = null;
        line(log, "stopped", "err");
      }
    }
    // --- PING STREAM ---
    if (e.target.id === "startPing") {
      const interval = Number(document.getElementById("interval").value || 2);
      const log = document.getElementById("logPing");
      log.innerHTML = "";
      if (esPing) esPing.close();

      const url = `${BASE}/items/stream-ping?interval=${encodeURIComponent(interval)}`;
      line(log, `Connecting: ${url}`, "ok");
      const es = new EventSource(url);
      esPing = es;

      es.addEventListener("hello", (ev) => line(log, `hello: ${ev.data}`, "ok"));
      es.addEventListener("ping", (ev) => {
        const data = safeParse(ev.data);
        line(log, `ping: ${typeof data === 'string' ? data : JSON.stringify(data)}`);
      });
      es.onmessage = (ev) => line(log, `message: ${ev.data}`);
      es.onerror = () => line(log, `error (network/disconnected)`, "err");
    }
    if (e.target.id === "stopPing") {
      const log = document.getElementById("logPing");
      if (esPing) {
        esPing.close();
        esPing = null;
        line(log, "stopped", "err");
      }
    }
  });
</script>
"""
