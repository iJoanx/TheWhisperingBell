import unreal
out = []
for n in ('GeometryScript_MeshSpatial', 'GeometryScriptRayHitResult', 'GeometryScriptSpatialQueryOptions', 'GeometryScriptDynamicMeshBVH'):
    c = getattr(unreal, n, None)
    out.append("%s: %s" % (n, [f for f in dir(c) if not f.startswith('_')][:40] if c else None))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump230.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
