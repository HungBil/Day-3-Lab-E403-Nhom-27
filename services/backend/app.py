"""
Backend API server for Travel Planner.
Serves the ReAct Agent and Chatbot via HTTP endpoints.
Frontend (chat.html) calls POST /api/chat to interact.
"""
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from urllib.parse import urlparse

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from src.agent.agent import ReActAgent
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


def _create_llm():
    """Create LLM provider based on .env configuration."""
    provider_name = os.getenv("DEFAULT_PROVIDER", "google").lower()
    model = os.getenv("DEFAULT_MODEL", "")

    if provider_name == "openai":
        from src.core.openai_provider import OpenAIProvider
        api_key = os.getenv("OPENAI_API_KEY")
        return OpenAIProvider(model_name=model or "gpt-4o", api_key=api_key)

    elif provider_name == "google":
        from src.core.gemini_provider import GeminiProvider
        api_key = os.getenv("GEMINI_API_KEY")
        return GeminiProvider(model_name=model or "gemini-2.0-flash", api_key=api_key)

    elif provider_name == "local":
        from src.core.local_provider import LocalProvider
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        return LocalProvider(model_path=model_path)

    raise ValueError(f"Unknown provider: {provider_name}")


# Initialize LLM and Agent once at startup
print("Initializing LLM provider...")
llm = _create_llm()
agent = ReActAgent(llm=llm, max_steps=10)
print(f"Ready! Provider: {os.getenv('DEFAULT_PROVIDER', 'google')}, Model: {llm.model_name}")


# Frontend directory for serving static files
FE_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


class TravelPlannerHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves static FE files and API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FE_DIR, **kwargs)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/chat":
            self._handle_chat()
        elif parsed.path == "/api/metrics":
            self._handle_metrics()
        else:
            self.send_error(404, "Not found")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self._json_response({"status": "ok", "provider": llm.model_name})
            return

        # Serve static files from frontend/
        super().do_GET()

    def _handle_chat(self):
        """POST /api/chat — Run the ReAct agent on user message."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            self._json_response({"error": f"Invalid JSON: {e}"}, status=400)
            return

        message = data.get("message", "").strip()
        if not message:
            self._json_response({"error": "Empty message"}, status=400)
            return

        logger.log_event("API_REQUEST", {"message": message})

        try:
            result = agent.run(message)

            # Format traces for FE
            fe_traces = []
            for t in result.get("traces", []):
                fe_traces.append({
                    "step": t["step"],
                    "thought": t.get("thought", ""),
                    "action": t.get("action", ""),
                    "observation": t.get("observation", ""),
                })

            response = {
                "reply": result["answer"],
                "steps": result["steps"],
                "status": result["status"],
                "traces": fe_traces,
            }

            logger.log_event("API_RESPONSE", {
                "status": result["status"],
                "steps": result["steps"],
                "answer_preview": result["answer"][:100],
            })

            self._json_response(response)

        except Exception as exc:
            logger.log_event("API_ERROR", {"error": str(exc)})
            self._json_response({"error": str(exc)}, status=500)

    def _handle_metrics(self):
        """POST /api/metrics — Return session metrics."""
        metrics = tracker.session_metrics
        summary = {
            "total_requests": len(metrics),
            "total_tokens": sum(m.get("total_tokens", 0) for m in metrics),
            "total_cost": sum(m.get("cost_estimate", 0) for m in metrics),
            "avg_latency_ms": (
                sum(m.get("latency_ms", 0) for m in metrics) / len(metrics)
                if metrics else 0
            ),
            "requests": metrics,
        }
        self._json_response(summary)

    def _json_response(self, data: dict, status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        """Suppress default access logs to keep console clean."""
        pass


def main():
    port = int(os.getenv("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), TravelPlannerHandler)
    print(f"\n🚀 Travel Planner server running at http://localhost:{port}")
    print(f"   Frontend:  http://localhost:{port}/index.html")
    print(f"   Chat:      http://localhost:{port}/chat.html")
    print(f"   API:       POST http://localhost:{port}/api/chat")
    print(f"   Health:    GET  http://localhost:{port}/api/health")
    print(f"\n   Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
