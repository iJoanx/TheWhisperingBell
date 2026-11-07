import sys, importlib, traceback, math
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    nodes = [a for a in sb._actors() if sb._is_node(a)]
    _, per = sb._gather(nodes, [])
    nd = [a for a in nodes if a.get_actor_label() == "SL_303_Crossing"][0]
    conns = sb._local_conns(nd, per[nd.get_path_name()])
    for k, c in enumerate(conns):
        out.append("arm %d h (%.3f,%.3f) ptype %s q %s mirror %s" % (k, c["h"].x, c["h"].y, c["ptype"], sb.PASSAGE_TYPES[c["ptype"]].get("water_half_width"), c.get("mirror")))
    out.append("mitres %s" % {k: tuple((round(p[0]), round(p[1])) for p in v) for k, v in sb._crossing_mitres(conns).items()})
    out.append("mouths %s" % sb._channel_mouths(conns))
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing")
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    n = 0
    for t in range(sb.gs("get_num_triangle_i_ds")(dyn)):
        vs = sb._tri_positions(dyn, t)
        if not vs: continue
        if not all(-130 < v.z < -70 for v in vs): continue
        nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        if nrm.length() < 1e-6: continue
        nz = nrm.normal().z
        if nz < 0.5: continue
        n += 1
        out.append("tri %d nz %.2f verts %s" % (t, nz, [(round(v.x), round(v.y), round(v.z, 1)) for v in vs]))
    out.append("upward faces in channel band: %d" % n)
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump250.txt", "w", encoding="utf-8").write("\n".join(out))
