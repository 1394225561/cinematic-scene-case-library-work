from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_URL = (
    "https://higgsfield.ai/generate"
    "?projectId=3caa2f3a-52b5-4293-9237-0c8f76c7158a"
)
WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = WORK_ROOT / "data" / "reports" / "network-capture.json"
CHROME_CANDIDATES = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
)
API_RESOURCE_TYPES = {"Fetch", "XHR"}
TEXT_MIME_MARKERS = ("json", "text", "javascript", "xml")
BLOCKED_MEDIA_PATTERNS = (
    "*.avif*",
    "*.gif*",
    "*.jpeg*",
    "*.jpg*",
    "*.m3u8*",
    "*.mov*",
    "*.mp3*",
    "*.mp4*",
    "*.png*",
    "*.webm*",
    "*.webp*",
)
EXCLUDED_CAPTURE_HOSTS = {
    "amplitude.higgsfield.ai",
    "dd.higgsfield.ai",
    "o4509169762697216.ingest.de.sentry.io",
    "www.google-analytics.com",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def find_browser(explicit_path: Path | None) -> Path:
    if explicit_path:
        if not explicit_path.is_file():
            raise FileNotFoundError(f"browser executable not found: {explicit_path}")
        return explicit_path
    for candidate in CHROME_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Chrome or Edge was not found in a supported location")


def read_devtools_port(profile_dir: Path, timeout: float) -> int:
    port_file = profile_dir / "DevToolsActivePort"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            first_line = port_file.read_text(encoding="utf-8").splitlines()[0]
            return int(first_line)
        except (FileNotFoundError, IndexError, ValueError, PermissionError):
            time.sleep(0.1)
    raise TimeoutError(f"DevToolsActivePort was not created within {timeout} seconds")


def local_json(url: str, timeout: float = 5.0) -> Any:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def find_page_websocket(port: int, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    endpoint = f"http://127.0.0.1:{port}/json/list"
    while time.monotonic() < deadline:
        try:
            targets = local_json(endpoint)
            for target in targets:
                if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                    return str(target["webSocketDebuggerUrl"])
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        time.sleep(0.1)
    raise TimeoutError(f"no debuggable page appeared within {timeout} seconds")


class WebSocket:
    def __init__(self, connection: socket.socket, initial_bytes: bytes = b"") -> None:
        self.connection = connection
        self.buffer = bytearray(initial_bytes)

    @classmethod
    def connect(cls, url: str, timeout: float = 10.0) -> "WebSocket":
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "ws" or not parsed.hostname or not parsed.port:
            raise ValueError(f"unsupported DevTools WebSocket URL: {url}")
        connection = socket.create_connection((parsed.hostname, parsed.port), timeout=timeout)
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        target = parsed.path or "/"
        if parsed.query:
            target += f"?{parsed.query}"
        request = (
            f"GET {target} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        connection.sendall(request.encode("ascii"))
        response = bytearray()
        while b"\r\n\r\n" not in response:
            chunk = connection.recv(4096)
            if not chunk:
                raise ConnectionError("DevTools WebSocket closed during handshake")
            response.extend(chunk)
            if len(response) > 64_000:
                raise ConnectionError("DevTools WebSocket handshake was unexpectedly large")
        header_bytes, initial_bytes = bytes(response).split(b"\r\n\r\n", 1)
        header_text = header_bytes.decode("iso-8859-1")
        if not header_text.startswith("HTTP/1.1 101"):
            raise ConnectionError(f"DevTools WebSocket handshake failed: {header_text.splitlines()[0]}")
        expected_accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if f"Sec-WebSocket-Accept: {expected_accept}".lower() not in header_text.lower():
            raise ConnectionError("DevTools WebSocket returned an invalid accept key")
        connection.settimeout(0.5)
        return cls(connection, initial_bytes)

    def _read_exact(self, size: int) -> bytes:
        while len(self.buffer) < size:
            chunk = self.connection.recv(max(4096, size - len(self.buffer)))
            if not chunk:
                raise ConnectionError("DevTools WebSocket closed")
            self.buffer.extend(chunk)
        value = bytes(self.buffer[:size])
        del self.buffer[:size]
        return value

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        first = 0x80 | opcode
        length = len(payload)
        mask = secrets.token_bytes(4)
        if length < 126:
            header = bytes((first, 0x80 | length))
        elif length <= 0xFFFF:
            header = bytes((first, 0x80 | 126)) + struct.pack("!H", length)
        else:
            header = bytes((first, 0x80 | 127)) + struct.pack("!Q", length)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.connection.sendall(header + mask + masked)

    def send_json(self, value: dict[str, Any]) -> None:
        self._send_frame(0x1, json.dumps(value, separators=(",", ":")).encode("utf-8"))

    def receive_json(self) -> dict[str, Any] | None:
        fragments = bytearray()
        message_opcode: int | None = None
        while True:
            first, second = self._read_exact(2)
            final = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            if opcode == 0x8:
                return None
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode in (0x1, 0x2):
                message_opcode = opcode
                fragments.extend(payload)
            elif opcode == 0x0 and message_opcode is not None:
                fragments.extend(payload)
            else:
                continue
            if not final:
                continue
            if message_opcode != 0x1:
                return None
            return json.loads(fragments.decode("utf-8"))

    def close(self) -> None:
        try:
            self._send_frame(0x8, b"")
        except OSError:
            pass
        self.connection.close()


class CdpCapture:
    def __init__(self, websocket: WebSocket, max_response_bytes: int) -> None:
        self.websocket = websocket
        self.max_response_bytes = max_response_bytes
        self.next_command_id = 0
        self.pending_commands: dict[int, tuple[str, str | None]] = {}
        self.requests: dict[str, dict[str, Any]] = {}
        self.errors: list[dict[str, Any]] = []
        self.page_loaded = False

    def send(self, method: str, params: dict[str, Any] | None = None, request_id: str | None = None) -> int:
        self.next_command_id += 1
        command_id = self.next_command_id
        self.pending_commands[command_id] = (method, request_id)
        message: dict[str, Any] = {"id": command_id, "method": method}
        if params is not None:
            message["params"] = params
        self.websocket.send_json(message)
        return command_id

    @staticmethod
    def _is_api_request(resource_type: str, url: str) -> bool:
        parsed = urllib.parse.urlsplit(url)
        return (
            resource_type in API_RESOURCE_TYPES
            and parsed.hostname not in EXCLUDED_CAPTURE_HOSTS
            and parsed.path != "/cdn-cgi/rum"
        )

    def _on_request(self, params: dict[str, Any]) -> None:
        request = params.get("request") or {}
        resource_type = str(params.get("type") or "")
        url = str(request.get("url") or "")
        if not self._is_api_request(resource_type, url):
            return
        request_id = str(params.get("requestId") or "")
        self.requests[request_id] = {
            "request_id": request_id,
            "resource_type": resource_type,
            "method": request.get("method"),
            "url": url,
            "post_data": request.get("postData"),
            "response": None,
            "body": None,
            "body_error": None,
        }

    def _on_response(self, params: dict[str, Any]) -> None:
        request_id = str(params.get("requestId") or "")
        entry = self.requests.get(request_id)
        if entry is None:
            return
        response = params.get("response") or {}
        entry["response"] = {
            "status": response.get("status"),
            "status_text": response.get("statusText"),
            "mime_type": response.get("mimeType"),
            "protocol": response.get("protocol"),
            "from_disk_cache": response.get("fromDiskCache"),
            "from_service_worker": response.get("fromServiceWorker"),
        }

    def _on_loading_finished(self, params: dict[str, Any]) -> None:
        request_id = str(params.get("requestId") or "")
        entry = self.requests.get(request_id)
        if entry is None or entry.get("response") is None:
            return
        encoded_length = int(params.get("encodedDataLength") or 0)
        entry["encoded_data_length"] = encoded_length
        mime_type = str(entry["response"].get("mime_type") or "").lower()
        if encoded_length > self.max_response_bytes:
            entry["body_error"] = f"response exceeds byte limit ({self.max_response_bytes})"
            return
        if mime_type and not any(marker in mime_type for marker in TEXT_MIME_MARKERS):
            entry["body_error"] = f"non-text response skipped ({mime_type})"
            return
        self.send("Network.getResponseBody", {"requestId": request_id}, request_id=request_id)

    def _on_loading_failed(self, params: dict[str, Any]) -> None:
        request_id = str(params.get("requestId") or "")
        entry = self.requests.get(request_id)
        if entry is not None:
            entry["body_error"] = str(params.get("errorText") or "loading failed")

    def _on_command_result(self, message: dict[str, Any]) -> None:
        command_id = int(message["id"])
        method, request_id = self.pending_commands.pop(command_id, ("unknown", None))
        if "error" in message:
            error = {"method": method, "request_id": request_id, "error": message["error"]}
            self.errors.append(error)
            if request_id and request_id in self.requests:
                self.requests[request_id]["body_error"] = json.dumps(message["error"])
            return
        if method != "Network.getResponseBody" or request_id is None:
            return
        result = message.get("result") or {}
        entry = self.requests.get(request_id)
        if entry is None:
            return
        body = result.get("body")
        if result.get("base64Encoded"):
            entry["body_error"] = "base64 response skipped"
        elif isinstance(body, str):
            entry["body"] = body

    def handle(self, message: dict[str, Any]) -> None:
        if "id" in message:
            self._on_command_result(message)
            return
        method = message.get("method")
        params = message.get("params") or {}
        if method == "Network.requestWillBeSent":
            self._on_request(params)
        elif method == "Network.responseReceived":
            self._on_response(params)
        elif method == "Network.loadingFinished":
            self._on_loading_finished(params)
        elif method == "Network.loadingFailed":
            self._on_loading_failed(params)
        elif method == "Page.loadEventFired":
            self.page_loaded = True

    def run(self, url: str, capture_seconds: float) -> None:
        self.send(
            "Network.enable",
            {
                "maxTotalBufferSize": self.max_response_bytes * 4,
                "maxResourceBufferSize": self.max_response_bytes,
            },
        )
        self.send("Network.setBlockedURLs", {"urls": list(BLOCKED_MEDIA_PATTERNS)})
        self.send("Page.enable")
        self.send("Page.navigate", {"url": url})
        deadline = time.monotonic() + capture_seconds
        while time.monotonic() < deadline:
            try:
                message = self.websocket.receive_json()
            except socket.timeout:
                continue
            if message is None:
                break
            self.handle(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture public Higgsfield XHR/fetch traffic through headless Chrome without third-party Python packages."
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--startup-timeout", type=float, default=15.0)
    parser.add_argument("--capture-seconds", type=float, default=20.0)
    parser.add_argument("--max-response-bytes", type=int, default=5_000_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {
        "schema_version": 1,
        "started_at": utc_now(),
        "target_url": args.url,
        "dependency_policy": "python-standard-library-plus-existing-headless-browser",
        "media_response_bodies_captured": False,
        "media_url_patterns_blocked": list(BLOCKED_MEDIA_PATTERNS),
        "requests": [],
        "errors": [],
    }
    browser_process: subprocess.Popen[bytes] | None = None
    websocket: WebSocket | None = None
    temp_directory: tempfile.TemporaryDirectory[str] | None = None
    temp_root = WORK_ROOT / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        browser = find_browser(args.browser)
        report["browser"] = str(browser)
        temp_directory = tempfile.TemporaryDirectory(prefix="higgsfield-cdp-", dir=temp_root)
        profile_dir = Path(temp_directory.name)
        command = [
            str(browser),
            "--headless=new",
            "--remote-debugging-port=0",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-background-networking",
            "--window-size=1440,1000",
            "about:blank",
        ]
        browser_process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        port = read_devtools_port(profile_dir, args.startup_timeout)
        websocket_url = find_page_websocket(port, args.startup_timeout)
        websocket = WebSocket.connect(websocket_url, timeout=args.startup_timeout)
        capture = CdpCapture(websocket, args.max_response_bytes)
        capture.run(args.url, args.capture_seconds)
        report["page_loaded"] = capture.page_loaded
        report["requests"] = list(capture.requests.values())
        report["errors"].extend(capture.errors)
    except Exception as error:
        report["errors"].append({"stage": "capture", "error": repr(error)})
    finally:
        if websocket is not None:
            websocket.close()
        if browser_process is not None and browser_process.poll() is None:
            browser_process.terminate()
            try:
                browser_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                browser_process.kill()
                browser_process.wait(timeout=5)
        if temp_directory is not None:
            temp_directory.cleanup()
        report["finished_at"] = utc_now()
        report["request_count"] = len(report["requests"])
        report["response_body_count"] = sum(
            1 for request in report["requests"] if request.get("body") is not None
        )
        write_json_atomic(args.output, report)

    print(
        json.dumps(
            {
                "page_loaded": report.get("page_loaded", False),
                "request_count": report["request_count"],
                "response_body_count": report["response_body_count"],
                "errors": len(report["errors"]),
                "report": str(args.output),
            },
            indent=2,
        )
    )
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
