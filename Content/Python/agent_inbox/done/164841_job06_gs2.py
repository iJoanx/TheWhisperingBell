import unreal
k = unreal.load_class(None, "/Script/GeometryScriptingCore.GeometryScriptLibrary_MeshBasicEditFunctions")
print("after load:", getattr(unreal, "GeometryScriptLibrary_MeshBasicEditFunctions", None))
print("DynamicMesh vertex methods:", [x for x in dir(unreal.DynamicMesh) if "vertex" in x.lower()][:20])
libs = [a for a in dir(unreal) if "MeshBasicEdit" in a or "MeshPrimitive" in a or "MeshBoolean" in a]
print("libs:", libs)
import sewer_builder as sb
for n in ["append_box", "apply_mesh_boolean", "add_vertex_to_mesh", "add_triangle_to_mesh", "copy_mesh_to_static_mesh"]:
    sb._GS_CACHE.pop(n, None)
    try:
        f = sb.gs(n); print(n, "->", f)
    except Exception as e:
        print(n, "MISSING")
