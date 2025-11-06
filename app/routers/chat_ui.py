# app/routers/chat_ui.py
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/chat", tags=["chat"])

@router.get("", response_class=HTMLResponse)
def chat_page():
    return HTMLResponse(content="""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Agent Chat</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; }
    body { margin: 0; background: #0b0f14; color: #e8eef6; }
    .wrap { max-width: 880px; margin: 32px auto; padding: 0 16px; }
    .card { background:#121826; border:1px solid #22304a; border-radius:12px; overflow:hidden; }
    .head { padding:16px 20px; border-bottom:1px solid #22304a; display:flex; gap:12px; align-items:center; }
    .badge { font-size:12px; padding:2px 8px; border-radius:999px; background:#1e2a3f; color:#a7c0ff; }
    .log  { padding:16px 20px; height:56vh; overflow:auto; }
    .row  { margin:12px 0; }
    .u { color:#b8ffd8; }
    .a { color:#ffd29e; }
    .bar { display:flex; gap:8px; padding:12px; border-top:1px solid #22304a; background:#0d1320; }
    input[type="text"] { flex:1; padding:12px; border-radius:10px; border:1px solid #22304a; background:#0b0f14; color:#e8eef6; outline:none; }
    button { padding:10px 14px; border-radius:10px; border:1px solid #2b3a5a; background:#18233a; color:#e8eef6; cursor:pointer; }
    button:hover { background:#22304a; }
    .row pre { margin:6px 0 0; white-space:pre-wrap; word-wrap:break-word; }
    .switch { margin-left:auto; display:flex; gap:6px; align-items:center; }
    select { background:#0b0f14; color:#e8eef6; border:1px solid #22304a; border-radius:8px; padding:6px 8px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="head">
        <div><strong>Company Data Assistant</strong></div>
        <span class="badge">LangChain tools</span>
        <div class="switch">
          <label for="backend">Backend:</label>
          <select id="backend">
            <option value="agent" selected>/qa/ask-agent</option>
            <option value="fast">/qa/ask-fast (classified)</option>
          </select>
        </div>
      </div>
      <div id="log" class="log"></div>
      <div class="bar">
        <input id="q" type="text" placeholder="Ask e.g. 'Who joined Engineering after 2024-01-01?'" />
        <button id="send">Send</button>
        <button id="clear">Clear</button>
      </div>
    </div>
  </div>

<script>
(() => {
  const log = document.getElementById('log');
  const q   = document.getElementById('q');
  const sendBtn = document.getElementById('send');
  const clearBtn = document.getElementById('clear');
  const backendSel = document.getElementById('backend');

  // simple in-memory history for /qa/ask-agent
  let history = []; // [{role:'user'|'assistant', content:'...'}]

  function addRow(role, text) {
    const div = document.createElement('div');
    div.className = 'row ' + (role === 'user' ? 'u' : 'a');
    const who = role === 'user' ? 'You' : 'Assistant';
    div.innerHTML = `<div><strong>${who}:</strong></div><pre>${escapeHtml(text || '')}</pre>`;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  function escapeHtml(str) {
    return (str || '').replace(/[&<>"']/g, m => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;', "'":'&#39;'
    }[m]));
  }

  async function ask(question) {
    const mode = backendSel.value; // 'agent' or 'sql'
    if (mode === 'agent' || mode === 'fast') {
      // New agent endpoint
      const url = mode === 'fast' ? '/qa/ask-fast' : '/qa/ask-agent';
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, history })
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error('HTTP ' + res.status + ': ' + txt);
      }
      const data = await res.json();
      return data.answer || '';
    } else {
      // Legacy SQL endpoint
      const res = await fetch('/qa/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error('HTTP ' + res.status + ': ' + txt);
      }
      const data = await res.json();
      // unify to a single string for display if your legacy schema differs
      return (data.answer || data.result || JSON.stringify(data));
    }
  }

  async function onSend() {
    const text = q.value.trim();
    if (!text) return;
    addRow('user', text);
    history.push({ role: 'user', content: text });
    q.value = '';
    try {
      const answer = await ask(text);
      addRow('assistant', answer);
      history.push({ role: 'assistant', content: answer });
    } catch (e) {
      const msg = 'Error: ' + (e?.message || e);
      addRow('assistant', msg);
      history.push({ role: 'assistant', content: msg });
    }
  }

  function onClear() {
    log.innerHTML = '';
    history = [];
  }

  sendBtn.addEventListener('click', onSend);
  clearBtn.addEventListener('click', onClear);
  q.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') onSend();
  });
})();
</script>
</body>
</html>
""")
