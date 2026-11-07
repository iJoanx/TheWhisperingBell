import sys, importlib, traceback, time
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    t0 = time.time()
    nodes = [a for a in sb._actors() if sb._is_node(a) and a.get_actor_label() == "SL_303_Crossing"]
    _, per = sb._gather([a for a in sb._actors() if sb._is_node(a)], [])
    conns = sb._local_conns(nodes[0], per[nodes[0].get_path_name()])
    out.append("arms: %s" % [(round(c["pitch"], 2), round(c["lead"]), round(c["h"].x, 2), round(c["h"].y, 2)) for c in conns])
    out.append("levels now: %s" % [round(x) for x in sb._crossing_levels(conns, sb.CROSSING_HUB)])
    n, failed = sb.rebake_crossings(["SL_303_Crossing"])
    out.append("rebaked %d in %.0fs, failed: %s" % (n, time.time() - t0, failed))
    # check: walkway-level vertices left off the plane inside the crossing
    sm = unreal.load_asset(sb.GENERATED_FOLDER + "/SM_SewerNode_SL_303_Crossing")
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    r = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    dyn = r[0] if isinstance(r, tuple) else dyn
    off = 0
    for vid in range(sb.gs("get_num_vertex_i_ds")(dyn)):
        q = sb.gs("get_vertex_position")(dyn, vid)
        q = q[0] if isinstance(q, tuple) else q
        if isinstance(q, unreal.Vector) and q.x * q.x + q.y * q.y < 259.0 ** 2 and 0.0 < abs(q.z) < 3.0:
            off += 1
    out.append("SL_303 floor vertices still off the walkway plane inside the crossing: %d" % off)
    out.append("collision primitives: %s" % unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_simple_collision_count(sm))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump234.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
