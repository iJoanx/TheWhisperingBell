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
    return tris
def risers(tris, zmin=-20.0, hmin=0.3, hmax=15.0):
    found = []
    for a, b, c in tris:
        n = (b - a).cross(c - a); L = n.length()
        if L < 1e-6: continue
        nz = abs(n.z) / L
        lo, hi = min(a.z, b.z, c.z), max(a.z, b.z, c.z)
        if nz < 0.35 and hmin < hi - lo < hmax and lo > zmin and hi < 25:
            found.append(((a + b + c) / 3.0, hi - lo, L / 2.0))
    return found
STATS = []
try:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    nodes = [a for a in eas.get_all_level_actors() if a.get_class().get_name() == 'BP_SewerNode_C' and 'Crossing' in a.get_actor_label()]
    out.append("crossing nodes: %d" % len(nodes))
    t0 = time.time()
    rows = []
    for nd in nodes:
        tot = cnt = 0; biggest = 0.0; meshes = []
        for comp in nd.get_components_by_class(unreal.StaticMeshComponent):
            sm = comp.static_mesh
            if not sm or 'Water' in sm.get_name(): continue
            meshes.append(sm.get_name())
            rs = [r for r in risers(mesh_tris(sm)) if r[1] < 3.0]
            cnt += len(rs); tot += sum(r[2] for r in rs); biggest = max([biggest] + [r[1] for r in rs])
            if 'SL_303' in nd.get_actor_label():
                out.append("SL_303 mesh %s: %d small risers, area %.0f cm2" % (sm.get_name(), len(rs), sum(r[2] for r in rs)))
                for p, h, area in sorted(rs, key=lambda r: -r[2])[:12]:
                    out.append("    riser %.1f cm high at (%+.0f,%+.0f,%+.1f) area %.0f" % (h, p.x, p.y, p.z, area))
        rows.append((tot, cnt, biggest, nd.get_actor_label(), meshes))
        STATS.append((cnt, tot, biggest, nd.get_actor_label()))
    out.append("measured in %.0fs" % (time.time() - t0))
    small = []
    for tot, cnt, big, lab, ms in rows:
        pass
    out.append("measured %d crossings" % len(rows))
    with_small = [r for r in STATS if r[0]]
    out.append("crossings with small steps (0.3-3 cm): %d of %d" % (len(with_small), len(STATS)))
    hist = {}
    for c, t, b, l in STATS:
        k = "0" if c == 0 else ("1-3" if c <= 3 else ("4-10" if c <= 10 else "11+"))
        hist[k] = hist.get(k, 0) + 1
    out.append("steps per crossing: %s" % hist)
    for c, t, b, l in sorted(STATS, reverse=True)[:15]:
        out.append("  %-20s steps=%3d area=%5.0f cm2 tallest=%.1f cm" % (l, c, t, b))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump229.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
