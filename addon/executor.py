import bpy
import io
import math
import traceback
from contextlib import redirect_stdout


def _handle_create_object(params: dict) -> dict:
    # Design Ref: §3.2 — use bpy.data directly, never bpy.ops
    # Plan SC: SC-01 — object creation must be reflected in Blender scene
    obj_type = params.get("type", "MESH").upper()
    name = params.get("name", "MCPObject")
    location = params.get("location", [0.0, 0.0, 0.0])
    size = float(params.get("size", 1.0))

    collection = bpy.context.scene.collection

    if obj_type == "MESH":
        mesh = bpy.data.meshes.new(name)
        # Default cube verts scaled by size
        s = size / 2
        verts = [
            (-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
            (-s, -s,  s), (s, -s,  s), (s, s,  s), (-s, s,  s),
        ]
        faces = [(0,1,2,3), (4,5,6,7), (0,1,5,4), (2,3,7,6), (1,2,6,5), (0,3,7,4)]
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
    elif obj_type == "LIGHT":
        light = bpy.data.lights.new(name, type="POINT")
        light.energy = 1000.0 * size
        obj = bpy.data.objects.new(name, light)
    elif obj_type == "CAMERA":
        cam = bpy.data.cameras.new(name)
        obj = bpy.data.objects.new(name, cam)
    elif obj_type == "EMPTY":
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_size = size
    else:
        return {"success": False, "error": f"Unsupported object type: {obj_type}"}

    obj.location = location
    collection.objects.link(obj)

    return {"success": True, "data": _object_info(obj)}


def _handle_modify_object(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "Missing required param: name"}

    obj = bpy.data.objects.get(name)
    if obj is None:
        return {"success": False, "error": f"Object '{name}' not found"}

    if "location" in params:
        obj.location = params["location"]

    if "rotation" in params:
        # Design Ref: §4.1 — tool input is degrees, convert to radians here
        rot_deg = params["rotation"]
        obj.rotation_euler = [math.radians(a) for a in rot_deg]

    if "scale" in params:
        obj.scale = params["scale"]

    if "name_new" in params:
        obj.name = params["name_new"]

    return {"success": True, "data": _object_info(obj)}


def _handle_delete_object(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "Missing required param: name"}

    obj = bpy.data.objects.get(name)
    if obj is None:
        return {"success": False, "error": f"Object '{name}' not found"}

    # Plan SC: SC-04 — clean removal including orphan data
    mesh = obj.data if obj.type == "MESH" else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh and mesh.users == 0:
        bpy.data.meshes.remove(mesh)

    return {"success": True, "data": {"deleted": name}}


def _handle_execute_python(params: dict) -> dict:
    # Plan SC: SC-02 — capture stdout and return to caller
    code = params.get("code", "")
    if not code:
        return {"success": False, "error": "Missing required param: code"}

    stdout_capture = io.StringIO()
    local_ns = {"bpy": bpy, "math": math}
    try:
        with redirect_stdout(stdout_capture):
            exec(code, local_ns)  # noqa: S102
        output = stdout_capture.getvalue()
        return {"success": True, "data": {"output": output}}
    except Exception:
        return {"success": False, "error": traceback.format_exc()}


def _handle_get_scene_info(params: dict) -> dict:
    scene = bpy.context.scene
    objects = [_object_info(obj) for obj in scene.objects]
    return {
        "success": True,
        "data": {
            "name": scene.name,
            "object_count": len(objects),
            "objects": objects,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
        },
    }


def _handle_get_object_info(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "Missing required param: name"}

    obj = bpy.data.objects.get(name)
    if obj is None:
        return {"success": False, "error": f"Object '{name}' not found"}

    return {"success": True, "data": _object_info(obj)}


def _object_info(obj) -> dict:
    return {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        # Design Ref: §5.1 — expose rotation in degrees for external callers
        "rotation": [math.degrees(a) for a in obj.rotation_euler],
        "scale": list(obj.scale),
        "visible": obj.visible_get(),
    }


COMMAND_HANDLERS = {
    "create_object": _handle_create_object,
    "modify_object": _handle_modify_object,
    "delete_object": _handle_delete_object,
    "execute_python": _handle_execute_python,
    "get_scene_info": _handle_get_scene_info,
    "get_object_info": _handle_get_object_info,
}


def execute(command: dict) -> dict:
    handler = COMMAND_HANDLERS.get(command.get("type"))
    if handler is None:
        return {"success": False, "error": f"Unknown command: {command.get('type')}"}
    return handler(command.get("params", {}))
