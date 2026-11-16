import unreal, collections
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump348.txt", "w", encoding="utf-8").write("\n".join(out))
GA, GQ = unreal.GeometryScript_AssetUtils, unreal.GeometryScript_MeshQueries
PATCHED = set()
for fn in ('dump341.txt', 'dump342.txt'):
    for l in open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\\" + fn).read().splitlines():
        if l.startswith('WROTE '): PATCHED.add(l.split()[1].rstrip(':'))
cache = {}
def uv5(sm):
    k = sm.get_name()
    if k in cache: return cache[k]
    dm = unreal.DynamicMesh()
    GA.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    c = collections.Counter()
    n = GQ.get_num_triangle_i_ds(dm)
    for t in range(0, n, max(1, n // 30)):
        u = [x for x in GQ.get_triangle_u_vs(dm, 5, t) if isinstance(x, unreal.Vector2D)]
        if u: c[(int(round(u[0].x)), round(u[0].y, 4))] += 1
    cache[k] = c.most_common(1)[0][0] if c else None
    return cache[k]
def boxdist(a, b):
    (ao, ae), (bo, be) = a, b
    d = 0.0
    for i in ('x', 'y', 'z'):
        g = abs(getattr(ao, i) - getattr(bo, i)) - getattr(ae, i) - getattr(be, i)
        if g > 0: d += g * g
    return d ** 0.5
try:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    towers, others = [], []
    prefixes = collections.Counter()
    for a in eas.get_all_level_actors():
        if not isinstance(a, unreal.StaticMeshActor): continue
        sm = a.static_mesh_component.static_mesh
        if not sm or not sm.get_path_name().startswith('/Game/Houses/'): continue
        o, e = a.get_actor_bounds(False)
        n = sm.get_name()
        prefixes['_'.join(n.split('_')[:2])] += 1
        (towers if n.startswith('SM_Towers') else others).append((n, sm, (o, e)))
    out.append("prefixes %s" % dict(prefixes))
    def pick(b, n_touch=50.0):
        touching = [h for h in others if boxdist(b, h[2]) < n_touch]
        if not touching: return None, []
        o = b[0]
        touching.sort(key=lambda h: (h[2][0].x - o.x) ** 2 + (h[2][0].y - o.y) ** 2)
        return touching[0], touching
    # 1) test the rule on the towers that were right from the start
    ok = bad = 0
    for n, sm, b in sorted(towers):
        if n in PATCHED: continue
        h, touching = pick(b)
        if not h: continue
        tc = uv5(sm)
        if uv5(h[1]) == tc: ok += 1
        else:
            bad += 1
            out.append("rule misses orig %s: tower %s, picked %s %s, touching %s" % (n, tc, h[0], uv5(h[1]), [(t[0], uv5(t[1])) for t in touching]))
    out.append("rule on original towers: %d right, %d wrong" % (ok, bad))
    # 2) write the attached house's code + random into each patched tower that touches a house
    opts = unreal.GeometryScriptCopyMeshToAssetOptions()
    for p, v in (('enable_recompute_normals', False), ('enable_recompute_tangents', False), ('enable_remove_degenerates', False), ('replace_materials', False)):
        try: opts.set_editor_property(p, v)
        except Exception: pass
    done_n = 0
    for n, sm, b in sorted(towers):
        if n not in PATCHED: continue
        h, touching = pick(b)
        if not h: continue
        hx, hy = uv5(h[1])
        dm = unreal.DynamicMesh()
        GA.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
        nt = GQ.get_num_triangle_i_ds(dm)
        for t in range(nt):
            tri = unreal.GeometryScriptUVTriangle()
            for k in ('uv0', 'uv1', 'uv2'): tri.set_editor_property(k, unreal.Vector2D(float(hx), float(hy)))
            unreal.GeometryScript_UVs.set_mesh_triangle_u_vs(dm, 5, t, tri, False)
        GA.copy_mesh_to_static_mesh(dm, sm, opts, unreal.GeometryScriptMeshWriteLOD())
        cache.pop(sm.get_name(), None)
        done_n += 1
        out.append("WROTE %s <- %s %s (now %s)" % (n, h[0], (hx, hy), uv5(sm)))
    out.append("towers matched to their house: %d" % done_n)
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
