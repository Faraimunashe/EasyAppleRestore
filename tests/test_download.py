from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from easyrestore.backend.download import DownloadCancelled, download_file


@pytest.fixture()
def http_file_server(tmp_path: Path):
    payload = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" * 1024
    source = tmp_path / "payload.bin"
    source.write_bytes(payload)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            data = source.read_bytes()
            range_header = self.headers.get("Range")
            if range_header and range_header.startswith("bytes="):
                start = int(range_header.split("=", 1)[1].split("-", 1)[0] or "0")
                chunk = data[start:]
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
                self.send_header("Content-Length", str(len(chunk)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self.wfile.write(chunk)
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/payload.bin"
    try:
        yield url, payload
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_download_full_file(tmp_path: Path, http_file_server) -> None:
    url, payload = http_file_server
    dest = tmp_path / "out.ipsw"
    progress: list[tuple[int, int | None]] = []
    result = download_file(url, dest, on_progress=lambda d, t: progress.append((d, t)))
    assert result.path == dest
    assert not result.resumed
    assert dest.read_bytes() == payload
    assert progress[-1][0] == len(payload)


def test_download_resumes_partial(tmp_path: Path, http_file_server) -> None:
    url, payload = http_file_server
    dest = tmp_path / "out.ipsw"
    partial = dest.with_suffix(".ipsw.partial")
    partial.write_bytes(payload[:100])
    result = download_file(url, dest, expected_size=len(payload))
    assert result.resumed
    assert dest.read_bytes() == payload
    assert not partial.exists()


def test_download_cancel(tmp_path: Path, http_file_server) -> None:
    url, _payload = http_file_server
    dest = tmp_path / "out.ipsw"
    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    with pytest.raises(DownloadCancelled):
        download_file(url, dest, chunk_size=16, should_cancel=should_cancel)
