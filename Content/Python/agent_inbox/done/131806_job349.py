import unreal, collections, math
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump349.txt", "w", encoding="utf-8").write("\n".join(out))
GA, GQ = unreal.GeometryScript_AssetUtils, unreal.GeometryScript_MeshQueries
def tuv(dm, ch, t): return [x for x in GQ.get_triangle_u_vs(dm, ch, t) if isinstance(x, unreal.Vector2D)]
def tpos(dm, t):
    r = GQ.get_triangle_positions(dm, t)
    return [x for x in r if isinstance(x, unreal.Vector)]
def report(name, limit=400):
    sm = unreal.load_asset('/Game/Houses/Meshes/' + name)
    dm = unreal.DynamicMesh()
    GA.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    n = GQ.get_num_triangle_i_ds(dm)
    out.append("== %s: %d tris" % (name, n))
    rows = []
    for t in range(n):
        p = tpos(dm, t); u0 = tuv(dm, 0, t); u1 = tuv(dm, 1, t); u2 = tuv(dm, 2, t)
        if len(p) < 3 or len(u0) < 3: continue
        zc = sum(q.z for q in p) / 3
        # texel density: uv length per cm along the longest edge
        dens = []
        for i in range(3):
            a, b = p[i], p[(i + 1) % 3]
            L = math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)
            ul = math.sqrt((u0[i].x - u0[(i + 1) % 3].x) ** 2 + (u0[i].y - u0[(i + 1) % 3].y) ** 2)
            if L > 1: dens.append(ul / L * 100)
        cls = round(1 - u1[0].y, 2) if u1 else None
        rows.append((zc, t, cls, round(max(dens), 3) if dens else None, [(round(q.x, 2), round(q.y, 2)) for q in u0], (round(u1[0].x, 2) if u1 else None), [(round(q.x, 1), round(1 - q.y, 1)) for q in u2][:1]))
    rows.sort()
    zmin = rows[0][0]
    for r in rows:
        if r[0] - zmin < 450:          # bottom part
            out.append("  z+%.0f tri %d class %s uv/m %s uv0 %s special %s rows/pk %s" % (r[0] - zmin, r[1], r[2], r[3], r[4], r[5], r[6]))
try:
    report('SM_Towers_Towers_114')
    report('SM_Towers_Towers_03')
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
