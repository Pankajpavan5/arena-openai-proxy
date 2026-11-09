import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
API_KEY = os.environ.get("API_KEY", "sk-render-arena-free")
UPSTREAM_URL = "https://text.pollinations.ai/openai/chat/completions"
MODELS_URL = "https://text.pollinations.ai/models"

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
            return False
        token = auth_header.replace("Bearer ", "").strip()
        return token == API_KEY

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self._send_json(200, {
                "status": "online",
                "message": "Render OpenAI Proxy is active",
                "docs": "Use /v1/models and /v1/chat/completions"
            })
            return

        if path in ("/v1/models", "/models"):
            if not self._verify_auth():
                self._send_json(401, {"error": {"message": "Invalid API key"}})
                return
            try:
                req = urllib.request.Request(MODELS_URL, headers={"User-Agent": "render-proxy"})
                with urllib.request.urlopen(req, timeout=10) as res:
                    raw = json.loads(res.read().decode("utf-8"))
                    models_list = [{"id": m.get("name", "openai-fast"), "object": "model"} for m in raw]
                    self._send_json(200, {"object": "list", "data": models_list})
            except Exception:
                self._send_json(200, {
                    "object": "list",
                    "data": [
                        {"id": "gpt-4o", "object": "model"},
                        {"id": "gpt-3.5-turbo", "object": "model"},
                        {"id": "openai-fast", "object": "model"}
                    ]
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
