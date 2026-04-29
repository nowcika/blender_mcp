import json
import socket
import struct


class BlenderClient:
    # Design Ref: §3.3 — 4-byte big-endian length prefix protocol for message framing
    def __init__(self, host: str = "localhost", port: int = 9999, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send_command(self, command_type: str, params: dict | None = None) -> dict:
        # Plan SC: SC-04 — catch all connection errors and return structured error
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                self._send(sock, {"type": command_type, "params": params or {}})
                return self._recv(sock)
        except ConnectionRefusedError:
            return {
                "success": False,
                "error": (
                    f"Cannot connect to Blender at {self.host}:{self.port}. "
                    "Make sure Blender is running and the MCP Add-on is active."
                ),
            }
        except TimeoutError:
            return {"success": False, "error": f"Blender response timed out after {self.timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _send(self, sock: socket.socket, msg: dict) -> None:
        data = json.dumps(msg).encode("utf-8")
        sock.sendall(struct.pack(">I", len(data)) + data)

    def _recv(self, sock: socket.socket) -> dict:
        raw_len = self._recv_exact(sock, 4)
        msg_len = struct.unpack(">I", raw_len)[0]
        data = self._recv_exact(sock, msg_len)
        return json.loads(data.decode("utf-8"))

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Blender closed the connection unexpectedly")
            buf += chunk
        return buf
