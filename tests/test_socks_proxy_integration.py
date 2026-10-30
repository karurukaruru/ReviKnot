"""Verify the installed OpenAI client can use a configured SOCKS proxy."""

import json
import socketserver
import threading

from openai import OpenAI


def test_openai_request_through_socks_proxy(monkeypatch):
    seen = {}

    class SocksProxy(socketserver.StreamRequestHandler):
        def handle(self):
            version, count = self.rfile.read(2)
            assert version == 5 and 0 in self.rfile.read(count)
            self.wfile.write(b"\x05\x00")
            self.wfile.flush()

            version, command, _, address_type = self.rfile.read(4)
            assert (version, command, address_type) == (5, 1, 3)
            length = self.rfile.read(1)[0]
            seen["host"] = self.rfile.read(length).decode("ascii")
            seen["port"] = int.from_bytes(self.rfile.read(2), "big")
            self.wfile.write(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x00")
            self.wfile.flush()

            seen["request"] = self.rfile.readline().decode("ascii").strip()
            headers = {}
            while (line := self.rfile.readline()) not in (b"\r\n", b""):
                name, value = line.decode("ascii").split(":", 1)
                headers[name.lower()] = value.strip()
            self.rfile.read(int(headers.get("content-length", "0")))
            body = json.dumps({
                "id": "mock-response", "object": "chat.completion", "created": 0,
                "model": "mock", "choices": [{"index": 0,
                    "message": {"role": "assistant", "content": "proxy-ok"},
                    "finish_reason": "stop"}],
            }).encode()
            self.wfile.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                + b"Connection: close\r\nContent-Length: " + str(len(body)).encode()
                + b"\r\n\r\n" + body
            )
            self.wfile.flush()

    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("no_proxy", "")

    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), SocksProxy) as proxy:
        proxy_url = f"socks5h://127.0.0.1:{proxy.server_address[1]}"
        monkeypatch.setenv("ALL_PROXY", proxy_url)
        monkeypatch.setenv("all_proxy", proxy_url)
        thread = threading.Thread(target=proxy.serve_forever, daemon=True)
        thread.start()
        try:
            with OpenAI(api_key="test-only", base_url="http://unit-test.invalid:18443/v1", max_retries=0, timeout=5.0) as client:
                response = client.chat.completions.create(
                    model="mock", messages=[{"role": "user", "content": "test"}]
                )
        finally:
            proxy.shutdown()
            thread.join(timeout=5)

    assert (seen["host"], seen["port"]) == ("unit-test.invalid", 18443)
    assert seen["request"].startswith("POST /v1/chat/completions ")
    assert response.choices[0].message.content == "proxy-ok"
