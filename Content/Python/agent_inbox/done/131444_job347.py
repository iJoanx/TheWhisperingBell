import unreal, collections
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump347.txt", "w", encoding="utf-8").write("\n".join(out))
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
    stats = collections.Counter()
    for n, sm, b in sorted(towers):
        best = sorted(others, key=lambda h: boxdist(b, h[2]))[:2]
        h = best[0]
        d = boxdist(b, h[2])
        tc, hc = uv5(sm), uv5(h[1])
        match = tc == hc
        tag = "PATCHED" if n in PATCHED else "orig"
        stats[(tag, d < 50, match)] += 1
        out.append("%s %s: tower %s | nearest %s at %.0f cm code %s | %s" % (tag, n, tc, h[0], d, hc, "MATCH" if match else "differs"))
    out.insert(1, "stats (tag, attached<50cm, same code+rand): %s" % dict(stats))
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
