"""Serve Stacks locally and proxy requests to optional local AI services."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, urlencode, urlparse


HOST = "127.0.0.1"
PORT = 8000
OLLAMA_URL = "http://127.0.0.1:11434"
PIPER_URL = "http://127.0.0.1:5000"
WEB_ROOT = Path(__file__).resolve().parent
MAX_REQUEST_BYTES = 64_000
MAX_BOOK_BYTES = 5_000_000
GUTENBERG_HOSTS = {"www.gutenberg.org", "gutenberg.org", "aleph.gutenberg.org"}


class StacksHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def _json(self, status: int, data: dict) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > MAX_REQUEST_BYTES:
            raise ValueError("Request body must be between 1 byte and 64 KB.")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object.")
        return data

    @staticmethod
    def _service_json(url: str, timeout: int = 3) -> dict:
        with urlopen(url, timeout=timeout) as response:
            return json.loads(response.read())

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/gutenberg/search":
            query = parse_qs(parsed.query).get("q", [""])[0].strip()
            if not query or len(query) > 160:
                self._json(400, {"error": "Search text must be between 1 and 160 characters."})
                return
            url = "https://gutendex.com/books/?" + urlencode(
                {"search": query, "languages": "en", "copyright": "false"}
            )
            try:
                result = self._service_json(url, timeout=20)
                self._json(200, result)
            except (HTTPError, URLError, TimeoutError, ValueError, OSError):
                self._json(502, {"error": "Project Gutenberg search is temporarily unavailable."})
            return

        if parsed.path == "/api/booktext":
            source_url = parse_qs(parsed.query).get("url", [""])[0]
            source = urlparse(source_url)
            if source.scheme != "https" or source.hostname not in GUTENBERG_HOSTS or not source.path.lower().endswith((".txt", ".txt.utf-8")):
                self._json(400, {"error": "Only Project Gutenberg plain-text files can be opened here."})
                return
            try:
                with urlopen(source_url, timeout=30) as response:
                    content_type = response.headers.get("Content-Type", "")
                    if "text/plain" not in content_type.lower():
                        self._json(415, {"error": "This Project Gutenberg address did not return plain text."})
                        return
                    content = response.read(MAX_BOOK_BYTES + 1)
                if len(content) > MAX_BOOK_BYTES:
                    self._json(413, {"error": "This text is larger than the 5 MB reader limit."})
                    return
                text = content.decode("utf-8-sig", errors="replace").encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(text)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(text)
            except HTTPError as error:
                self._json(502, {"error": f"Project Gutenberg returned HTTP {error.code}."})
            except (URLError, TimeoutError, OSError):
                self._json(502, {"error": "Could not download this Project Gutenberg text."})
            return

        if parsed.path != "/api/status":
            return super().do_GET()

        result = {"ollama": {"available": False, "models": []}, "piper": {"available": False}}
        try:
            tags = self._service_json(f"{OLLAMA_URL}/api/tags")
            models = [item.get("name", "") for item in tags.get("models", []) if item.get("name")]
            result["ollama"] = {"available": True, "models": models}
        except (URLError, TimeoutError, ValueError, OSError):
            pass

        try:
            info = self._service_json(f"{PIPER_URL}/info")
            result["piper"] = {
                "available": True,
                "voice": info.get("name") or info.get("voice") or "Local Piper voice",
            }
        except (URLError, TimeoutError, ValueError, OSError):
            pass

        self._json(200, result)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/ollama/chat", "/api/tts"}:
            self._json(404, {"error": "Unknown API route."})
            return

        try:
            data = self._read_json()
        except (ValueError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})
            return

        if path == "/api/ollama/chat":
            messages = data.get("messages")
            if not isinstance(messages, list) or not messages:
                self._json(400, {"error": "A non-empty messages array is required."})
                return

            try:
                installed = self._service_json(f"{OLLAMA_URL}/api/tags").get("models", [])
                names = [item.get("name", "") for item in installed]
                requested = data.get("model", "")
                model = requested if requested in names else next(
                    (name for name in names if "deepseek" in name.lower()),
                    names[0] if names else "",
                )
                if not model:
                    self._json(503, {"error": "No local Ollama model is available. Start Ollama and install a model first."})
                    return

                body = json.dumps({"model": model, "messages": messages, "stream": False}).encode("utf-8")
                request = Request(
                    f"{OLLAMA_URL}/api/chat",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=240) as response:
                    answer = json.loads(response.read())
                self._json(200, {"model": model, "reply": answer.get("message", {}).get("content", "")})
            except HTTPError as error:
                self._json(502, {"error": f"Ollama returned HTTP {error.code}. Check the model name and Ollama status."})
            except (URLError, TimeoutError, ValueError, OSError) as error:
                self._json(503, {"error": f"Could not reach Ollama: {error}"})
            return

        text = data.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 20_000:
            self._json(400, {"error": "Text must be between 1 and 20,000 characters."})
            return
        try:
            request = Request(
                f"{PIPER_URL}/synthesize",
                data=json.dumps({"text": text}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=180) as response:
                audio = response.read()
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(audio)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(audio)
        except HTTPError as error:
            self._json(502, {"error": f"Piper returned HTTP {error.code}."})
        except (URLError, TimeoutError, OSError):
            self._json(503, {"error": "Local Piper voice is not running. See the README for setup."})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), StacksHandler)
    print(f"Stacks is running at http://{HOST}:{PORT}")
    print("This development server accepts connections only from this computer.")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Stacks.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
