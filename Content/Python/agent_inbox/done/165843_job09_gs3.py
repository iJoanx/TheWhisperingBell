import unreal, importlib
import sewer_builder as sb
importlib.reload(sb)
owners = {}
for attr in dir(unreal):
    if attr.startswith("GeometryScript") and callable(getattr(getattr(unreal, attr), "add_vertex_to_mesh", None)):
        owners[attr] = 1
print("libraries with add_vertex_to_mesh:", list(owners))
for n in ["add_vertex_to_mesh", "add_triangle_to_mesh", "append_box", "copy_mesh_to_static_mesh"]:
    try:
        f = sb.gs(n); print(n, "->", f)
    except Exception as e:
        print(n, "MISSING", e)
m = unreal.DynamicMesh()
try:
    r = sb.gs("add_vertex_to_mesh")(m, unreal.Vector(1, 2, 3), False)
    print("call ok:", r)
except Exception as e:
    print("call failed:", e)
