import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
VALID_KEYS = {
    os.environ.get("API_KEY", "sk-arena-termux-free"),
    "sk-arena-termux-free",
    "sk-render-arena-free"
}

UPSTREAM_URL = "https://text.pollinations.ai/openai/chat/completions"

POPULAR_MODELS = [
    {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
    {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai"},
    {"id": "gpt-4-turbo", "object": "model", "owned_by": "openai"},
    {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
    {"id": "claude-3-5-sonnet", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-opus", "object": "model", "owned_by": "anthropic"},
    {"id": "gemini-2.0-flash", "object": "model", "owned_by": "google"},
    {"id": "gemini-1.5-pro", "object": "model", "owned_by": "google"},
    {"id": "deepseek-r1", "object": "model", "owned_by": "deepseek"},
    {"id": "deepseek-v3", "object": "model", "owned_by": "deepseek"},
    {"id": "openai-fast", "object": "model", "owned_by": "arena"},
    {"id": "gpt-oss-20b", "object": "model", "owned_by": "arena"}
]

class OpenAIProxyHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _verify_auth(self):
        auth_header = self.headers.get("Authorization", "")
        if not auth_header:
            return True
        token = auth_header.replace("Bearer ", "").strip()
        return (token in VALID_KEYS) or token.startswith("sk-")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self._send_json(200, {
                "status": "online",
                "message": "Render OpenAI Proxy is active",
                "endpoints": ["/v1/models", "/v1/chat/completions"]
            })
            return

        if path in ("/v1/models", "/models"):
            self._send_json(200, {
                "object": "list",
                "data": POPULAR_MODELS
            })
            return

        self._send_json(404, {"error": {"message": "Not found"}})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path not in ("/v1/chat/completions", "/chat/completions"):
            self._send_json(404, {"error": {"message": "Endpoint not found"}})
            return

        if not self._verify_auth():
            self._send_json(401, {"error": {"message": "Invalid API key"}})
            return

        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len)

        try:
            body = json.loads(post_data.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": {"message": "Invalid JSON body"}})
            return

        body["model"] = "openai-fast"
        modified_data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            UPSTREAM_URL,
            data=modified_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "render-openai-proxy"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                response_data = res.read()
                self.send_response(res.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(response_data)
        except urllib.error.HTTPError as e:
            self._send_json(e.code, {"error": {"message": e.read().decode("utf-8")}})
        except Exception as e:
            self._send_json(500, {"error": {"message": str(e)}})

    def log_message(self, format, *args):
        pass

def main():
    server = HTTPServer(("0.0.0.0", PORT), OpenAIProxyHandler)
    print(f"Proxy server running on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    main()
