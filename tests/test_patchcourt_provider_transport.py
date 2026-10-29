"""Exercise the real urllib transport against a local HTTP fixture only."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
import unittest
from unittest.mock import patch

from patchcourt import providers


@contextmanager
def local_response(body, *, status=200, trickle=False):
    stopped = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            # Consume the fixture request before closing the response socket;
            # leaving POST bytes unread can cause a TCP reset on Windows.
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                if trickle:
                    for value in body:
                        self.wfile.write(bytes([value]))
                        self.wfile.flush()
                        if stopped.wait(0.02):
                            break
                else:
                    self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        base = "http://127.0.0.1:" + str(server.server_port)
        with patch.object(providers, "NEBIUS_BASE", base), patch("urllib.request.getproxies", return_value={}):
            yield base + "/chat/completions"
    finally:
        stopped.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class ProviderTransportTests(unittest.TestCase):
    def test_complete_success_and_http_error_bodies_remain_available(self):
        for status, body in ((200, b'{"choices":[]}'), (401, b'{"error":"denied"}')):
            with self.subTest(status=status), local_response(body, status=status) as url:
                actual_status, headers, raw = providers._transport(url, "synthetic-key", {})
            self.assertEqual(actual_status, status)
            self.assertEqual(raw, body.decode("utf-8"))
            self.assertIn("Content-Type", headers)

    def test_trickling_response_becomes_one_preserved_failure_instead_of_extending_forever(self):
        # Every byte arrives before the socket's idle timeout. A single read()
        # would keep receiving for over two seconds instead of enforcing a
        # response budget. This must fail after the intervening deadline check.
        body = b'{"content":"' + b"a" * 100 + b'"}'
        with local_response(body, trickle=True), patch.object(providers, "TIMEOUT", 0.15), patch.dict(
                "os.environ", {"NEBIUS_API_KEY": "synthetic-key"}, clear=True):
            started = time.monotonic()
            record = providers.request("nebius", {"model": "nvidia/Nemotron-test", "max_tokens": 1})
            elapsed = time.monotonic() - started
        self.assertEqual(record["status"], "FAIL")
        self.assertIn("TimeoutError", record["reason"])
        self.assertIn("elapsed read budget", record["reason"])
        self.assertLess(elapsed, 1.0)
        self.assertNotIn("synthetic-key", str(record))

    def test_chunked_reader_preserves_the_maximum_response_size(self):
        for size, exceeds_limit in ((1000, False), (1001, True)):
            with self.subTest(size=size), local_response(b"a" * size) as url, patch.object(providers, "MAX_BYTES", 1000):
                if exceeds_limit:
                    with self.assertRaisesRegex(ValueError, "Response exceeds"):
                        providers._transport(url, "synthetic-key", {})
                else:
                    self.assertEqual(len(providers._transport(url, "synthetic-key", {})[2]), 1000)


if __name__ == "__main__":
    unittest.main()
