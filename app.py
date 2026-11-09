import os
import json
import time
import base64
import urllib.request
import urllib.error
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
ADMIN_USER = os.environ.get("ADMIN_USER", "xfreexareana.ai")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "xfreexareana.ai@778605")

VALID_KEYS = {
    os.environ.get("API_KEY", "sk-arena-termux-free"),
    "sk-arena-termux-free",
    "sk-render-arena-free"
}

UPSTREAM_URL = "https://text.pollinations.ai/openai/chat/completions"

# Global Analytics Stats
STATS = {
    "start_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    "total_requests": 0,
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_tokens": 0,
    "openai_requests": 0,
    "anthropic_requests": 0,
    "recent_logs": []
}

POPULAR_MODELS = [
    {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
    {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai"},
    {"id": "gpt-4-turbo", "object": "model", "owned_by": "openai"},
    {"id": "gpt-4", "object": "model", "owned_by": "openai"},
    {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
    {"id": "o1-preview", "object": "model", "owned_by": "openai"},
    {"id": "o1-mini", "object": "model", "owned_by": "openai"},
    {"id": "claude-3-5-sonnet", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-5-sonnet-20241022", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-5-haiku", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-opus", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-sonnet", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-haiku", "object": "model", "owned_by": "anthropic"},
    {"id": "deepseek-r1", "object": "model", "owned_by": "deepseek"},
    {"id": "deepseek-v3", "object": "model", "owned_by": "deepseek"},
    {"id": "deepseek-coder", "object": "model", "owned_by": "deepseek"},
    {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
    {"id": "gemini-2.0-flash", "object": "model", "owned_by": "google"},
    {"id": "gemini-2.0-flash-exp", "object": "model", "owned_by": "google"},
    {"id": "gemini-1.5-pro", "object": "model", "owned_by": "google"},
    {"id": "gemini-1.5-flash", "object": "model", "owned_by": "google"},
    {"id": "gemma-2-27b-it", "object": "model", "owned_by": "google"},
    {"id": "meta-llama/llama-3.3-70b-instruct", "object": "model", "owned_by": "meta"},
    {"id": "meta-llama/llama-3.1-405b-instruct", "object": "model", "owned_by": "meta"},
    {"id": "meta-llama/llama-3.1-70b-instruct", "object": "model", "owned_by": "meta"},
    {"id": "meta-llama/llama-3.1-8b-instruct", "object": "model", "owned_by": "meta"},
    {"id": "llama-3-70b", "object": "model", "owned_by": "meta"},
    {"id": "llama-3-8b", "object": "model", "owned_by": "meta"},
    {"id": "qwen/qwen-2.5-coder-32b-instruct", "object": "model", "owned_by": "qwen"},
    {"id": "qwen/qwen-2.5-72b-instruct", "object": "model", "owned_by": "qwen"},
    {"id": "mistralai/mistral-large-2407", "object": "model", "owned_by": "mistral"},
    {"id": "mistralai/mixtral-8x22b-instruct", "object": "model", "owned_by": "mistral"},
    {"id": "codestral-latest", "object": "model", "owned_by": "mistral"},
    {"id": "openai-fast", "object": "model", "owned_by": "arena"},
    {"id": "gpt-oss-20b", "object": "model", "owned_by": "arena"}
]

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Arena AI Proxy Dashboard</title>
<style>
  :root {
    --bg: #0f172a; --card: #1e293b; --border: #334155; --text: #f8fafc;
    --muted: #94a3b8; --primary: #38bdf8; --success: #4ade80; --purple: #a855f7;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  body { background: var(--bg); color: var(--text); padding: 20px; line-height: 1.5; }
  .container { max-width: 1100px; margin: 0 auto; }
  .header { display: flex; justify-content: space-between; align-items: center; border-b: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 24px; flex-wrap: wrap; gap: 10px; }
  .title { font-size: 1.5rem; font-weight: 700; color: var(--primary); }
  .badge { background: #0369a1; padding: 4px 10px; border-radius: 999px; font-size: 0.8rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .card-label { color: var(--muted); font-size: 0.85rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
  .card-val { font-size: 2rem; font-weight: 800; margin-top: 8px; }
  .c-blue { color: var(--primary); }
  .c-green { color: var(--success); }
  .c-purple { color: var(--purple); }
  .table-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left; }
  th { color: var(--muted); padding: 12px; border-bottom: 1px solid var(--border); }
  td { padding: 12px; border-bottom: 1px solid #1e293b; }
  tr:hover td { background: #243248; }
  .btn-refresh { background: var(--primary); color: #000; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; }
</style>
<script>
  async function reloadData() {
    const res = await fetch('/api/stats');
    const d = await res.json();
    document.getElementById('total-req').innerText = d.total_requests;
    document.getElementById('total-tok').innerText = d.total_tokens.toLocaleString();
    document.getElementById('prompt-tok').innerText = d.total_prompt_tokens.toLocaleString();
    document.getElementById('comp-tok').innerText = d.total_completion_tokens.toLocaleString();
    document.getElementById('openai-req').innerText = d.openai_requests;
    document.getElementById('anthropic-req').innerText = d.anthropic_requests;
    
    const tbody = document.getElementById('log-rows');
    tbody.innerHTML = '';
    if (!d.recent_logs || d.recent_logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--muted)">No requests yet</td></tr>';
      return;
    }
    d.recent_logs.forEach(l => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${l.time}</td><td><span style="color:var(--primary)">${l.type}</span></td><td>${l.model}</td><td>${l.tokens}</td><td style="color:var(--success)">${l.status}</td>`;
      tbody.appendChild(tr);
    });
  }
  setInterval(reloadData, 3000);
</script>
</head>
<body onload="reloadData()">
  <div class="container">
    <div class="header">
      <div>
        <div class="title">⚡ Arena AI Proxy Dashboard</div>
        <div style="color: var(--muted); font-size: 0.85rem; margin-top: 4px;">Admin: xfreexareana.ai &bull; Server Online</div>
      </div>
      <div>
        <button class="btn-refresh" onclick="reloadData()">Refresh</button>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="card-label">Total API Calls</div>
        <div class="card-val c-blue" id="total-req">0</div>
      </div>
      <div class="card">
        <div class="card-label">Total Tokens Used</div>
        <div class="card-val c-green" id="total-tok">0</div>
      </div>
      <div class="card">
        <div class="card-label">Prompt Tokens</div>
        <div class="card-val" id="prompt-tok">0</div>
      </div>
      <div class="card">
        <div class="card-label">Completion Tokens</div>
        <div class="card-val c-purple" id="comp-tok">0</div>
      </div>
      <div class="card">
        <div class="card-label">OpenAI Endpoints</div>
        <div class="card-val" id="openai-req">0</div>
      </div>
      <div class="card">
        <div class="card-label">Anthropic / Messages</div>
        <div class="card-val" id="anthropic-req">0</div>
      </div>
    </div>

    <div class="table-card">
      <h3 style="margin-bottom: 16px; font-size: 1.1rem;">Recent API Requests</h3>
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Endpoint</th>
            <th>Model Requested</th>
            <th>Tokens</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="log-rows">
          <tr><td colspan="5" style="text-align:center;color:var(--muted)">Loading...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""

class OpenAIProxyHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-api-key, anthropic-version")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-api-key, anthropic-version")
        self.end_headers()

    def _check_admin_auth(self):
        auth_header = self.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return False
        try:
            encoded = auth_header.split(" ", 1)[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            user, pwd = decoded.split(":", 1)
            return user == ADMIN_USER and pwd == ADMIN_PASS
        except Exception:
            return False

    def _request_auth(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Admin Dashboard"')
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>401 Unauthorized</h1><p>Access denied.</p>")

    def _verify_api_auth(self):
        auth_header = self.headers.get("Authorization", "") or self.headers.get("x-api-key", "")
        if not auth_header:
            return True
        token = auth_header.replace("Bearer ", "").strip()
        return (token in VALID_KEYS) or token.startswith("sk-")

    def do_GET(self):
        path = self.path.split("?")[0]
        
        # Dashboard Route with HTTP Basic Auth
        if path in ("/dashboard", "/dashboard/"):
            if not self._check_admin_auth():
                self._request_auth()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            return

        # Dashboard Stats JSON API
        if path == "/api/stats":
            if not self._check_admin_auth():
                self._send_json(401, {"error": "Unauthorized"})
                return
            self._send_json(200, STATS)
            return

        # Root Endpoint
        if path == "/":
            self._send_json(200, {
                "status": "online",
                "message": "Render Proxy is active",
                "dashboard": "/dashboard",
                "endpoints": ["/v1/models", "/v1/chat/completions", "/v1/messages"]
            })
            return

        # Models Endpoint
        if path in ("/v1/models", "/models"):
            self._send_json(200, {
                "object": "list",
                "data": POPULAR_MODELS
            })
            return

        self._send_json(404, {"error": {"message": f"Endpoint not found: {path}"}})

    def do_POST(self):
        path = self.path.split("?")[0]
        if not self._verify_api_auth():
            self._send_json(401, {"error": {"message": "Invalid API key"}})
            return

        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len)

        try:
            body = json.loads(post_data.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": {"message": "Invalid JSON body"}})
            return

        req_model = body.get("model", "unknown")

        # Anthropic /v1/messages
        if path in ("/v1/messages", "/messages"):
            system_prompt = body.get("system", "")
            anthropic_messages = body.get("messages", [])
            openai_messages = []
            
            if system_prompt:
                if isinstance(system_prompt, list):
                    sys_text = "\n".join([item.get("text", "") for item in system_prompt if isinstance(item, dict)])
                else:
                    sys_text = str(system_prompt)
                openai_messages.append({"role": "system", "content": sys_text})

            for m in anthropic_messages:
                content = m.get("content", "")
                if isinstance(content, list):
                    text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                    content = "\n".join(text_parts)
                openai_messages.append({"role": m.get("role", "user"), "content": content})

            payload = {"model": "openai-fast", "messages": openai_messages}

            req = urllib.request.Request(
                UPSTREAM_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "render-proxy"}
            )

            try:
                with urllib.request.urlopen(req, timeout=60) as res:
                    upstream_data = json.loads(res.read().decode("utf-8"))
                    text_out = upstream_data["choices"][0]["message"]["content"]
                    
                    p_tok = upstream_data.get("usage", {}).get("prompt_tokens", 50)
                    c_tok = upstream_data.get("usage", {}).get("completion_tokens", 80)
                    t_tok = p_tok + c_tok
                    
                    # Update Stats
                    STATS["total_requests"] += 1
                    STATS["anthropic_requests"] += 1
                    STATS["total_prompt_tokens"] += p_tok
                    STATS["total_completion_tokens"] += c_tok
                    STATS["total_tokens"] += t_tok
                    STATS["recent_logs"].insert(0, {
                        "time": datetime.utcnow().strftime("%H:%M:%S"),
                        "type": "POST /v1/messages",
                        "model": req_model,
                        "tokens": f"{t_tok} (p:{p_tok}, c:{c_tok})",
                        "status": "200 OK"
                    })
                    STATS["recent_logs"] = STATS["recent_logs"][:25]

                    anthropic_resp = {
                        "id": upstream_data.get("id", "msg_123"),
                        "type": "message",
                        "role": "assistant",
                        "model": req_model,
                        "content": [{"type": "text", "text": text_out}],
                        "stop_reason": "end_turn",
                        "stop_sequence": None,
                        "usage": {"input_tokens": p_tok, "output_tokens": c_tok}
                    }
                    self._send_json(200, anthropic_resp)
            except Exception as e:
                self._send_json(500, {"type": "error", "error": {"type": "api_error", "message": str(e)}})
            return

        # OpenAI /v1/chat/completions
        if path in ("/v1/chat/completions", "/chat/completions"):
            body["model"] = "openai-fast"
            req = urllib.request.Request(
                UPSTREAM_URL,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "render-openai-proxy"}
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as res:
                    response_data = res.read()
                    upstream_data = json.loads(response_data.decode("utf-8"))
                    
                    p_tok = upstream_data.get("usage", {}).get("prompt_tokens", 40)
                    c_tok = upstream_data.get("usage", {}).get("completion_tokens", 60)
                    t_tok = p_tok + c_tok
                    
                    # Update Stats
                    STATS["total_requests"] += 1
                    STATS["openai_requests"] += 1
                    STATS["total_prompt_tokens"] += p_tok
                    STATS["total_completion_tokens"] += c_tok
                    STATS["total_tokens"] += t_tok
                    STATS["recent_logs"].insert(0, {
                        "time": datetime.utcnow().strftime("%H:%M:%S"),
                        "type": "POST /v1/chat/completions",
                        "model": req_model,
                        "tokens": f"{t_tok} (p:{p_tok}, c:{c_tok})",
                        "status": "200 OK"
                    })
                    STATS["recent_logs"] = STATS["recent_logs"][:25]

                    self.send_response(res.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(response_data)
            except urllib.error.HTTPError as e:
                self._send_json(e.code, {"error": {"message": e.read().decode("utf-8")}})
            except Exception as e:
                self._send_json(500, {"error": {"message": str(e)}})
            return

        self._send_json(404, {"error": {"message": f"Endpoint not found: {path}"}})

    def log_message(self, format, *args):
        pass

def main():
    server = HTTPServer(("0.0.0.0", PORT), OpenAIProxyHandler)
    print(f"Proxy server running on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    main()
