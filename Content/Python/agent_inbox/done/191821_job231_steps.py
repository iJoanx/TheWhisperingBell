import unreal, traceback, time, math
out = []
GS = unreal.GeometryScript_AssetUtils
def mesh_tris(sm):
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = GS.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    MQ = unreal.GeometryScript_MeshQueries
    fn = getattr(MQ, 'get_all_triangle_i_ds', None) or getattr(MQ, 'get_all_triangle_ids')
    ids = fn(dyn)
    if isinstance(ids, tuple): ids = [x for x in ids if isinstance(x, unreal.GeometryScriptIndexList)][0]
    ids = unreal.GeometryScript_List.convert_index_list_to_array(ids)
    tris = []
    for t in ids:
        r = unreal.GeometryScript_MeshQueries.get_triangle_positions(dyn, t)
        # returns (vertex1, vertex2, vertex3, is_valid) in some form
        vs = [v for v in r if isinstance(v, unreal.Vector)]
        if len(vs) == 3: tris.append(vs)
    return tris, dyn

MS = unreal.GeometryScript_MeshSpatial
def first(x, typ):
    if isinstance(x, typ): return x
    if isinstance(x, tuple):
        for v in x:
            if isinstance(v, typ): return v
    return None
def floor_z(dyn, bvh, x, y, ztop):
    r = MS.find_nearest_ray_intersection_with_mesh(dyn, bvh, unreal.Vector(x, y, ztop), unreal.Vector(0, 0, -1), unreal.GeometryScriptSpatialQueryOptions())
    h = first(r, unreal.GeometryScriptRayHitResult)
    if h is None or not h.get_editor_property('hit'): return None
    return h.get_editor_property('hit_position').z
def real_steps(tris, dyn):
    bvh = first(MS.build_bvh_for_mesh(dyn), unreal.GeometryScriptDynamicMeshBVH)
    found = []
    for a, b, c in tris:
        n = (b - a).cross(c - a); L = n.length()
        if L < 1e-6: continue
        nz = abs(n.z) / L
        lo, hi = min(a.z, b.z, c.z), max(a.z, b.z, c.z)
        if not (nz < 0.35 and 0.3 < hi - lo < 15.0 and lo > -20 and hi < 25): continue
        hx, hy = n.x, n.y; hl = (hx * hx + hy * hy) ** 0.5
        if hl < 1e-6: continue
        hx, hy = hx / hl, hy / hl
        m = (a + b + c) / 3.0
        za = floor_z(dyn, bvh, m.x + hx * 4, m.y + hy * 4, hi + 3)
        zb = floor_z(dyn, bvh, m.x - hx * 4, m.y - hy * 4, hi + 3)
        if za is None or zb is None: continue
        d = abs(za - zb)
        if 0.3 < d < 15.0 and min(za, zb) > -20:
            found.append((m, d, L / 2.0))
    return found
STATS = []
try:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    nodes = [a for a in eas.get_all_level_actors() if a.get_class().get_name() == 'BP_SewerNode_C' and 'Crossing' in a.get_actor_label()]
    t0 = time.time()
    for nd in nodes:
        allsteps = []
        for comp in nd.get_components_by_class(unreal.StaticMeshComponent):
            sm = comp.static_mesh
            if not sm or 'Water' in sm.get_name(): continue
            tris, dyn = mesh_tris(sm)
            allsteps += real_steps(tris, dyn)
        small = [s for s in allsteps if s[1] < 3.0]
        STATS.append((len(small), len(allsteps) - len(small), max([0.0] + [s[1] for s in small]), nd.get_actor_label()))
        if 'SL_303' in nd.get_actor_label():
            out.append("SL_303 real floor steps (floor height differs on the two sides):")
            for m, d, ar in sorted(allsteps, key=lambda s: -s[2])[:20]:
                out.append("   %.1f cm at (%+.0f,%+.0f) area %.0f" % (d, m.x, m.y, ar))
    out.append("measured %d crossings in %.0fs" % (len(STATS), time.time() - t0))
    hist = {}
    for c, big, t, l in STATS:
        k = "0" if c == 0 else ("1-3" if c <= 3 else ("4-10" if c <= 10 else "11+"))
        hist[k] = hist.get(k, 0) + 1
    out.append("real small floor steps (0.3-3 cm) per crossing: %s" % hist)
    out.append("crossings with real 3-15 cm floor steps: %d" % sum(1 for s in STATS if s[1]))
    for c, big, t, l in sorted(STATS, reverse=True)[:12]:
        out.append("  %-20s small=%3d bigger=%3d tallest small=%.1f" % (l, c, big, t))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump231.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
