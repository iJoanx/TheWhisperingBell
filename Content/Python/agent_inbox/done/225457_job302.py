import sys, traceback, math
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_305_Crossing")
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    rows = []
    for t in range(sb.gs("get_num_triangle_i_ds")(dyn)):
        vs = sb._tri_positions(dyn, t)
        if not vs: continue
        if not all(-101 < v.z < 2 for v in vs): continue
        nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        area = nrm.length() / 2
        if area < 0.5: continue
        nz = abs(nrm.normal().z)
        if 0.15 < nz < 0.95:
            r = sb.gs("get_triangle_u_vs")(dyn, 0, t)
            uvs = [u for u in r if isinstance(u, unreal.Vector2D)] if isinstance(r, tuple) else []
            c1 = sb.gs("get_triangle_u_vs")(dyn, 1, t)
            cell = [u for u in c1 if isinstance(u, unreal.Vector2D)] if isinstance(c1, tuple) else []
            rows.append((area, t, nz, [(round(v.x, 1), round(v.y, 1), round(v.z, 1)) for v in vs], [(round(u.x * 64, 1), round(u.y * 64, 1)) for u in uvs], (round(cell[0].x, 3), round(cell[0].y, 3)) if cell else None))
    rows.sort(reverse=True)
    out.append("slanted faces between channel bottom and walkway: %d" % len(rows))
    for r in rows[:40]:
        out.append("  tri %d area %.1f |nz| %.2f v %s uv %s cell %s" % (r[1], r[0], r[2], r[3], r[4], r[5]))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump302.txt", "w", encoding="utf-8").write("\n".join(out))
