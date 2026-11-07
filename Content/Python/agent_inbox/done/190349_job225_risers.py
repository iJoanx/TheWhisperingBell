import unreal, traceback, time, math
out = []
GS = unreal.GeometryScript_AssetUtils
def mesh_tris(sm):
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = GS.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    ids = unreal.GeometryScript_MeshQueries.get_all_triangle_i_ds(dyn) if hasattr(unreal.GeometryScript_MeshQueries, 'get_all_triangle_i_ds') else unreal.GeometryScript_MeshQueries.get_all_triangle_ids(dyn)
    if isinstance(ids, tuple): ids = ids[0]
    tris = []
    for t in ids.get_editor_property('list') if hasattr(ids, 'get_editor_property') else ids:
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
            rs = risers(mesh_tris(sm))
            cnt += len(rs); tot += sum(r[2] for r in rs); biggest = max([biggest] + [r[1] for r in rs])
            if 'SL_303' in nd.get_actor_label():
                out.append("SL_303 mesh %s: %d small risers, area %.0f cm2" % (sm.get_name(), len(rs), sum(r[2] for r in rs)))
                for p, h, area in sorted(rs, key=lambda r: -r[2])[:12]:
                    out.append("    riser %.1f cm high at (%+.0f,%+.0f,%+.1f) area %.0f" % (h, p.x, p.y, p.z, area))
        rows.append((tot, cnt, biggest, nd.get_actor_label(), meshes))
    out.append("measured in %.0fs" % (time.time() - t0))
    rows.sort(reverse=True)
    out.append("crossings with small risers: %d of %d" % (sum(1 for r in rows if r[1]), len(rows)))
    for tot, cnt, big, lab, ms in rows[:40]:
        out.append("  %-28s risers=%3d area=%6.0f cm2 tallest=%.1f cm  %s" % (lab, cnt, tot, big, ms[:2]))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump225.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
