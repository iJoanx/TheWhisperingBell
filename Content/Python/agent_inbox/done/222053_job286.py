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
        out.append("arm %d h(%.3f,%.3f) pitch %.2f lead %.1f mirror %s s_start %.1f" % (k, c["h"].x, c["h"].y, c["pitch"], c["lead"], c.get("mirror"), sb.CROSSING_HUB + c["lead"]))
    e = sb._wall_edge_for(conns[0], -1.0, 120.0)
    out.append("arm0 wall edge t=-120: %s uv0 %s uv400 %s" % (e[:2], e[3], e[4]))
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing")
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    hx, hy = conns[0]["h"].x, conns[0]["h"].y
    for t in range(sb.gs("get_num_triangle_i_ds")(dyn)):
        vs = sb._tri_positions(dyn, t)
        if not vs: continue
        nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        if nrm.length() < 1e-4: continue
        nn = nrm.normal()
        if abs(nn.z) > 0.2: continue
        sides = [-v.x * hy + v.y * hx for v in vs]
        if max(abs(sd + 120) for sd in sides) > 2 and max(abs(sd + 60) for sd in sides) > 2: continue
        al = [v.x * hx + v.y * hy for v in vs]
        if not (max(al) > 300 or min(al) < -250): continue
        r = sb.gs("get_triangle_u_vs")(dyn, 0, t)
        uvs = [u for u in r if isinstance(u, unreal.Vector2D)] if isinstance(r, tuple) else []
        out.append("tri %d t%.0f: %s" % (t, sum(sides) / 3, [(round(a, 1), round(v.z, 1), round(u.x * 64, 2), round(u.y * 64, 2)) for a, v, u in zip(al, vs, uvs)]))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump286.txt", "w", encoding="utf-8").write("\n".join(out))
