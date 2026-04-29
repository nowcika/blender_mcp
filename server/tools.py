import json

from mcp.server.fastmcp import FastMCP

from .blender_client import BlenderClient


# Design Ref: §3.4 — all 6 MCP tools registered here; BlenderClient is injected
def register_tools(mcp: FastMCP, blender: BlenderClient) -> None:

    @mcp.tool()
    def create_object(
        type: str,
        name: str,
        location: list[float] | None = None,
        size: float = 1.0,
    ) -> str:
        """Create a new object in the Blender scene.

        type: Object type — MESH, LIGHT, CAMERA, or EMPTY
        name: Name for the new object
        location: [x, y, z] position in meters (default: [0, 0, 0])
        size: Size multiplier (default: 1.0)
        """
        result = blender.send_command("create_object", {
            "type": type,
            "name": name,
            "location": location or [0.0, 0.0, 0.0],
            "size": size,
        })
        return _format(result)

    @mcp.tool()
    def modify_object(
        name: str,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
        name_new: str | None = None,
    ) -> str:
        """Modify properties of an existing Blender object.

        name: Name of the object to modify
        location: New [x, y, z] position in meters
        rotation: New [x, y, z] rotation in DEGREES (converted to radians internally)
        scale: New [x, y, z] scale factors
        name_new: Rename the object to this name
        """
        # Design Ref: §4.1 — rotation accepted as degrees for UX; executor converts to radians
        params: dict = {"name": name}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale
        if name_new is not None:
            params["name_new"] = name_new
        return _format(blender.send_command("modify_object", params))

    @mcp.tool()
    def delete_object(name: str) -> str:
        """Delete an object from the Blender scene.

        name: Exact name of the object to delete
        """
        return _format(blender.send_command("delete_object", {"name": name}))

    @mcp.tool()
    def execute_python(code: str) -> str:
        """Execute arbitrary Python code inside Blender.

        code: Valid Python code string. Has access to bpy and math.
        Returns captured stdout output.
        """
        # Plan SC: SC-02 — Python exec result must be returned to Claude
        return _format(blender.send_command("execute_python", {"code": code}))

    @mcp.tool()
    def get_scene_info() -> str:
        """Return information about the current Blender scene and all objects in it."""
        return _format(blender.send_command("get_scene_info"))

    @mcp.tool()
    def get_object_info(name: str) -> str:
        """Return detailed properties of a specific Blender object.

        name: Exact name of the object
        """
        return _format(blender.send_command("get_object_info", {"name": name}))


def _format(result: dict) -> str:
    if result.get("success"):
        data = result.get("data", {})
        return json.dumps(data, indent=2, ensure_ascii=False)
    return f"Error: {result.get('error', 'Unknown error')}"
