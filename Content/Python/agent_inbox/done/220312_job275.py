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
    mouths = sb._channel_mouths(conns)
    out.append("mouths %s" % mouths)
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing")
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    for k, (D1, D2) in mouths.items():
        dx, dy = D2[0] - D1[0], D2[1] - D1[1]; ln = math.hypot(dx, dy)
        nx, ny = -dy / ln, dx / ln
        cross, near = 0, 0
        for t in range(sb.gs("get_num_triangle_i_ds")(dyn)):
            vs = sb._tri_positions(dyn, t)
            if not vs or max(abs(v.z + 100) for v in vs) > 3: continue
            nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
            if nrm.length() < 1e-6 or abs(nrm.normal().z) < 0.9: continue
            sd = [(v.x - D1[0]) * nx + (v.y - D1[1]) * ny for v in vs]
            al = [((v.x - D1[0]) * dx + (v.y - D1[1]) * dy) / ln for v in vs]
            if max(al) < -5 or min(al) > ln + 5: continue
            if min(sd) < -0.5 and max(sd) > 0.5:
                cross += 1
                r = sb.gs("get_triangle_u_vs")(dyn, 0, t)
                uvs = [u for u in r if isinstance(u, unreal.Vector2D)] if isinstance(r, tuple) else []
                out.append("  crossing tri %d side %s along %s uv %s" % (t, [round(x, 1) for x in sd], [round(x) for x in al], [(round(u.x, 3), round(u.y, 3)) for u in uvs]))
            elif min(abs(x) for x in sd) < 0.5:
                near += 1
        out.append("mouth of arm %d: length %.0f; floor tris crossing the line: %d, touching it: %d" % (k, ln, cross, near))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump275.txt", "w", encoding="utf-8").write("\n".join(out))
