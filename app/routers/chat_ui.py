# app/routers/chat_ui.py
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Company Q&A Chat</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 0; background: #0f172a; color: #e2e8f0; }
    .wrap { max-width: 820px; margin: 0 auto; padding: 24px; }
    h1 { font-size: 20px; margin: 0 0 16px; color: #93c5fd; }
    .chat { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 16px; min-height: 60vh; }
    .msg { margin: 12px 0; line-height: 1.45; }
    .user { color: #fef3c7; }
    .bot { color: #d1fae5; }
    .meta { font-size: 12px; color: #9ca3af; margin-top: 6px; white-space: pre-wrap; }
    form { display: flex; gap: 8px; margin-top: 12px; }
    input[type=text] { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #1f2937; background: #0b1220; color: #e5e7eb; }
    button { padding: 12px 16px; border-radius: 8px; border: 0; background: #2563eb; color: white; cursor: pointer; }
    button:disabled { opacity: .6; cursor: not-allowed; }
    details { margin-top: 6px; }
    summary { cursor: pointer; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Company Q&A Chat</h1>
    <div id="chat" class="chat"></div>
    <form id="form">
      <input id="input" type="text" placeholder="Ask about employees, departments, projects, attendance..." required />
      <button id="send" type="submit">Send</button>
    </form>
  </div>

  <script>
    const chatEl = document.getElementById('chat');
    const formEl = document.getElementById('form');
    const inputEl = document.getElementById('input');
    const sendEl = document.getElementById('send');

    function addMsg(role, text, meta) {
      const div = document.createElement('div');
      div.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
      div.innerHTML = '<strong>' + (role === 'user' ? 'You' : 'Assistant') + ':</strong> ' + text;
      if (meta) {
        const md = document.createElement('div');
        md.className = 'meta';
        md.innerHTML = meta;
        div.appendChild(md);
      }
      chatEl.appendChild(div);
      chatEl.scrollTop = chatEl.scrollHeight;
    }

    formEl.addEventListener('submit', async (e) => {
      e.preventDefault();
      const q = inputEl.value.trim();
      if (!q) return;
      inputEl.value = '';
      addMsg('user', q);
      sendEl.disabled = true;

      try {
        const res = await fetch('/qa/ask', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ question: q })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Request failed');

        const meta =
          '<details><summary>Details</summary>' +
          '<div><strong>SQL</strong></div><code>' + (data.sql || '').replace(/</g,'&lt;') + '</code>' +
          '<div style="margin-top:6px;"><strong>Rows</strong></div><code>' + JSON.stringify(data.rows, null, 2).replace(/</g,'&lt;') + '</code>' +
          '</details>';

        addMsg('bot', data.answer || '(no answer)', meta);
      } catch (err) {
        addMsg('bot', 'Error: ' + err.message);
      } finally {
        sendEl.disabled = false;
      }
    });
  </script>
</body>
</html>
"""

@router.get("/chat", response_class=HTMLResponse)
def chat_ui():
    return HTML
