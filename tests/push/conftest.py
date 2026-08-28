import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest


class RequestLog:
    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.responses: dict[str, dict] = {}

    def record(self, path: str, query: dict, body: dict) -> None:
        self.requests.append({"path": path, "query": query, "body": body})

    def response_for(self, path: str) -> dict:
        return self.responses.get(path, {"errcode": 0, "errmsg": "ok"})


def _make_handler(log: RequestLog):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length)
            body = json.loads(raw_body) if raw_body else {}
            query = parse_qs(parsed.query)
            log.record(parsed.path, query, body)

            response_body = log.response_for(parsed.path)
            payload = json.dumps(response_body).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format_str: str, *args) -> None:
            pass

    return Handler


@pytest.fixture
def local_dingtalk_server():
    """Real local HTTP server standing in for DingTalk's webhook endpoint --
    same "no mocked transport" preference as tests/collector/conftest.py's
    local_fixture_server. Captures each request's path/query(incl. signature
    params)/JSON body; response bodies can be overridden per-path via
    `log.responses[path] = {...}` to simulate a DingTalk-side business
    rejection."""
    log = RequestLog()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(log))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    base_url = f"http://{host}:{port}"
    try:
        yield base_url, log
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
