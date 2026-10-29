"""A desktop launch must open its own bound server, including an ephemeral port."""
import io
from unittest.mock import patch

import pytest

from patchcourt.cli import serve_static
from tests.test_patchcourt_release_review import FakeConnection


def test_static_ephemeral_port_opens_and_authorizes_the_bound_address(tmp_path):
    (tmp_path / "index.html").write_text("fresh-export", encoding="utf-8")
    (tmp_path / "report.json").write_text("{}", encoding="utf-8")
    connections = []

    class Server:
        def __init__(self, address, handler):
            assert address == ("127.0.0.1", 0)
            self.server_address = ("127.0.0.1", 49152)
            self.server_name, self.server_port = self.server_address
            self.handler = handler
            self.closed = False

        def serve_forever(self):
            browser.assert_called_once_with("http://127.0.0.1:49152")
            for host in ("127.0.0.1:49152", "127.0.0.1:0", "example.invalid:49152"):
                connection = FakeConnection(f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())
                self.handler(connection, ("127.0.0.1", 60000), self)
                connections.append(bytes(connection.output))

        def server_close(self):
            self.closed = True

    with patch("http.server.ThreadingHTTPServer", Server), patch("webbrowser.open") as browser, patch(
            "sys.stdout", new_callable=io.StringIO) as output, patch("sys.stderr", new_callable=io.StringIO):
        assert serve_static(tmp_path, 0, open_browser=True) == 0
    assert "http://127.0.0.1:49152" in output.getvalue()
    assert b"200 OK" in connections[0] and b"fresh-export" in connections[0]
    assert all(b"403" in row.split(b"\r\n", 1)[0] for row in connections[1:])


def test_a_failed_bind_never_opens_an_unrelated_server(tmp_path):
    (tmp_path / "index.html").write_text("fresh-export", encoding="utf-8")
    (tmp_path / "report.json").write_text("{}", encoding="utf-8")
    with patch("http.server.ThreadingHTTPServer", side_effect=OSError("address in use")), patch(
            "webbrowser.open") as browser, pytest.raises(OSError, match="address in use"):
        serve_static(tmp_path, 8765, open_browser=True)
    browser.assert_not_called()


@pytest.mark.parametrize("port", [-1, 65536])
def test_invalid_port_has_an_actionable_error_without_binding(tmp_path, port):
    with patch("http.server.ThreadingHTTPServer") as server, pytest.raises(ValueError, match="0 to 65535"):
        serve_static(tmp_path, port)
    server.assert_not_called()
