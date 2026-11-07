import sys, importlib, traceback, math
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_305_Crossing")
    out.append("asset %s" % sm.get_path_name())
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    nodes = [a for a in sb._actors() if sb._is_node(a)]
    nd = [a for a in nodes if a.get_actor_label() == "SL_305_Crossing"][0]
    comp = nd.get_component_by_class(unreal.StaticMeshComponent)
    out.append("actor uses %s" % (comp.static_mesh.get_path_name() if comp.static_mesh else None))
    for t in range(sb.gs("get_num_triangle_i_ds")(dyn)):
        vs = sb._tri_positions(dyn, t)
        if not vs or not any(abs(v.x + 71.0) < 0.6 and abs(v.y - 13.5) < 0.6 and abs(v.z + 84.0) < 0.6 for v in vs): continue
        nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        nn = nrm.normal() if nrm.length() > 1e-9 else unreal.Vector(0, 0, 0)
        r = sb.gs("get_triangle_u_vs")(dyn, 0, t)
        uvs = [u for u in r if isinstance(u, unreal.Vector2D)] if isinstance(r, tuple) else []
        out.append("tri %d area %.3f n(%.2f,%.2f,%.2f) v %s uvpx %s" % (t, nrm.length() / 2, nn.x, nn.y, nn.z, [(round(v.x, 1), round(v.y, 1), round(v.z, 1)) for v in vs], [(round(u.x * 64, 2), round(u.y * 64, 2)) for u in uvs]))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump301.txt", "w", encoding="utf-8").write("\n".join(out))
