# bl_info is kept for backward compatibility with Blender < 4.2.
# Blender 4.2+ / 5.x uses blender_manifest.toml (Extension system).
bl_info = {
    "name": "Blender MCP",
    "author": "blender_mcp",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > MCP",
    "description": "MCP server for AI-driven Blender control",
    "category": "Interface",
}

import bpy
import socket
import threading
import json
import struct
import os
from . import executor

HOST = "localhost"
PORT = int(os.environ.get("BLENDER_MCP_PORT", 9999))

_server_instance = None


class BlenderMCPServer:
    # Design Ref: §3.1 — daemon thread + bpy.app.timers for thread safety
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self._socket = None
        self._thread = None
        self._running = False
        self._pending_command = None
        self._pending_result = None
        self._command_event = threading.Event()
        self._result_event = threading.Event()

    def start(self):
        self._running = True
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.host, self.port))
        self._socket.listen(1)
        self._socket.settimeout(1.0)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        bpy.app.timers.register(self._process_command, persistent=True)

    def stop(self):
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
        if bpy.app.timers.is_registered(self._process_command):
            bpy.app.timers.unregister(self._process_command)

    def _serve(self):
        while self._running:
            try:
                conn, _ = self._socket.accept()
                self._handle_client(conn)
            except socket.timeout:
                continue
            except OSError:
                break

    def _recv_message(self, conn):
        raw_len = self._recv_exact(conn, 4)
        if raw_len is None:
            return None
        msg_len = struct.unpack(">I", raw_len)[0]
        data = self._recv_exact(conn, msg_len)
        if data is None:
            return None
        return json.loads(data.decode("utf-8"))

    def _recv_exact(self, conn, n):
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

    def _send_message(self, conn, msg):
        data = json.dumps(msg).encode("utf-8")
        conn.sendall(struct.pack(">I", len(data)) + data)

    def _handle_client(self, conn):
        with conn:
            while self._running:
                try:
                    command = self._recv_message(conn)
                    if command is None:
                        break
                    # Plan SC: SC-04 — queue command; result comes from main thread
                    self._pending_command = command
                    self._result_event.clear()
                    self._command_event.set()
                    if not self._result_event.wait(timeout=15.0):
                        result = {"success": False, "error": "Blender main thread timeout"}
                    else:
                        result = self._pending_result or {"success": False, "error": "No result"}
                    self._send_message(conn, result)
                except Exception as e:
                    try:
                        self._send_message(conn, {"success": False, "error": str(e)})
                    except Exception:
                        pass
                    break

    def _process_command(self):
        # Design Ref: §6.2 — bpy must only be called from Blender main thread
        if self._command_event.is_set():
            self._command_event.clear()
            command = self._pending_command
            if command is not None:
                try:
                    self._pending_result = executor.execute(command)
                except Exception as e:
                    self._pending_result = {"success": False, "error": str(e)}
                self._result_event.set()
        return 0.05


class BLENDERMCP_OT_Start(bpy.types.Operator):
    bl_idname = "blendermcp.start"
    bl_label = "Start MCP Server"
    bl_description = "Start the Blender MCP socket server"

    def execute(self, context):
        global _server_instance
        if _server_instance and _server_instance._running:
            self.report({"WARNING"}, "Server already running")
            return {"CANCELLED"}
        _server_instance = BlenderMCPServer()
        _server_instance.start()
        context.scene.blendermcp_running = True
        self.report({"INFO"}, f"MCP Server started on {HOST}:{PORT}")
        return {"FINISHED"}


class BLENDERMCP_OT_Stop(bpy.types.Operator):
    bl_idname = "blendermcp.stop"
    bl_label = "Stop MCP Server"
    bl_description = "Stop the Blender MCP socket server"

    def execute(self, context):
        global _server_instance
        if _server_instance:
            _server_instance.stop()
            _server_instance = None
        context.scene.blendermcp_running = False
        self.report({"INFO"}, "MCP Server stopped")
        return {"FINISHED"}


class BLENDERMCP_PT_Panel(bpy.types.Panel):
    bl_label = "Blender MCP"
    bl_idname = "BLENDERMCP_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MCP"

    def draw(self, context):
        layout = self.layout
        running = context.scene.blendermcp_running
        layout.label(text=f"Port: {PORT}")
        if running:
            layout.label(text="Status: Running", icon="CHECKMARK")
            layout.operator("blendermcp.stop", icon="PAUSE")
        else:
            layout.label(text="Status: Stopped", icon="X")
            layout.operator("blendermcp.start", icon="PLAY")


def register():
    bpy.utils.register_class(BLENDERMCP_OT_Start)
    bpy.utils.register_class(BLENDERMCP_OT_Stop)
    bpy.utils.register_class(BLENDERMCP_PT_Panel)
    bpy.types.Scene.blendermcp_running = bpy.props.BoolProperty(default=False)


def unregister():
    global _server_instance
    if _server_instance:
        _server_instance.stop()
        _server_instance = None
    bpy.utils.unregister_class(BLENDERMCP_PT_Panel)
    bpy.utils.unregister_class(BLENDERMCP_OT_Stop)
    bpy.utils.unregister_class(BLENDERMCP_OT_Start)
    del bpy.types.Scene.blendermcp_running
