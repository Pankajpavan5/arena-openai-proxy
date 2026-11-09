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
    # OpenAI Models
    {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
    {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai"},
    {"id": "gpt-4-turbo", "object": "model", "owned_by": "openai"},
    {"id": "gpt-4", "object": "model", "owned_by": "openai"},
    {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
    {"id": "o1-preview", "object": "model", "owned_by": "openai"},
    {"id": "o1-mini", "object": "model", "owned_by": "openai"},

    # Anthropic Claude Models
    {"id": "claude-3-5-sonnet", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-5-sonnet-20241022", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-5-haiku", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-opus", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-sonnet", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-3-haiku", "object": "model", "owned_by": "anthropic"},

    # DeepSeek Reasoning & Chat Models
    {"id": "deepseek-r1", "object": "model", "owned_by": "deepseek"},
    {"id": "deepseek-v3", "object": "model", "owned_by": "deepseek"},
    {"id": "deepseek-coder", "object": "model", "owned_by": "deepseek"},
    {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},

    # Google Gemini Models
    {"id": "gemini-2.0-flash", "object": "model", "owned_by": "google"},
    {"id": "gemini-2.0-flash-exp", "object": "model", "owned_by": "google"},
    {"id": "gemini-1.5-pro", "object": "model", "owned_by": "google"},
    {"id": "gemini-1.5-flash", "object": "model", "owned_by": "google"},
    {"id": "gemma-2-27b-it", "object": "model", "owned_by": "google"},

    # Meta LLaMA Models
    {"id": "meta-llama/llama-3.3-70b-instruct", "object": "model", "owned_by": "meta"},
    {"id": "meta-llama/llama-3.1-405b-instruct", "object": "model", "owned_by": "meta"},
    {"id": "meta-llama/llama-3.1-70b-instruct", "object": "model", "owned_by": "meta"},
    {"id": "meta-llama/llama-3.1-8b-instruct", "object": "model", "owned_by": "meta"},
    {"id": "llama-3-70b", "object": "model", "owned_by": "meta"},
    {"id": "llama-3-8b", "object": "model", "owned_by": "meta"},

    # Qwen & Mistral Open Weights
    {"id": "qwen/qwen-2.5-coder-32b-instruct", "object": "model", "owned_by": "qwen"},
    {"id": "qwen/qwen-2.5-72b-instruct", "object": "model", "owned_by": "qwen"},
    {"id": "mistralai/mistral-large-2407", "object": "model", "owned_by": "mistral"},
    {"id": "mistralai/mixtral-8x22b-instruct", "object": "model", "owned_by": "mistral"},
    {"id": "codestral-latest", "object": "model", "owned_by": "mistral"},

    # Arena OSS Reasoning
    {"id": "openai-fast", "object": "model", "owned_by": "arena"},
    {"id": "gpt-oss-20b", "object": "model", "owned_by": "arena"}
]


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

    def _verify_auth(self):
        auth_header = self.headers.get("Authorization", "") or self.headers.get("x-api-key", "")
        if not auth_header:
            return True
        token = auth_header.replace("Bearer ", "").strip()
        return (token in VALID_KEYS) or token.startswith("sk-")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self._send_json(200, {
                "status": "online",
                "message": "Render Proxy is active",
                "endpoints": ["/v1/models", "/v1/chat/completions", "/v1/messages"]
            })
            return

        if path in ("/v1/models", "/models"):
            self._send_json(200, {
                "object": "list",
                "data": POPULAR_MODELS
            })
            return

        self._send_json(404, {"error": {"message": f"Endpoint not found: {path}"}})

    def do_POST(self):
        path = self.path.split("?")[0]
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

        # Handle Anthropic /v1/messages endpoint
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
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    content = "\n".join(text_parts)
                openai_messages.append({"role": m.get("role", "user"), "content": content})

            payload = {
                "model": "openai-fast",
                "messages": openai_messages
            }

            req = urllib.request.Request(
                UPSTREAM_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "render-proxy"}
            )

            try:
                with urllib.request.urlopen(req, timeout=60) as res:
                    upstream_data = json.loads(res.read().decode("utf-8"))
                    text_out = upstream_data["choices"][0]["message"]["content"]
                    
                    # Return Anthropic-format response
                    anthropic_resp = {
                        "id": upstream_data.get("id", "msg_123"),
                        "type": "message",
                        "role": "assistant",
                        "model": body.get("model", "claude-3-5-sonnet"),
                        "content": [{"type": "text", "text": text_out}],
                        "stop_reason": "end_turn",
                        "stop_sequence": None,
                        "usage": {
                            "input_tokens": upstream_data.get("usage", {}).get("prompt_tokens", 10),
                            "output_tokens": upstream_data.get("usage", {}).get("completion_tokens", 20)
                        }
                    }
                    self._send_json(200, anthropic_resp)
            except Exception as e:
                self._send_json(500, {"type": "error", "error": {"type": "api_error", "message": str(e)}})
            return

        # Handle OpenAI /v1/chat/completions endpoint
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
