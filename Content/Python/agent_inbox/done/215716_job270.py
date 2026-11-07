import sys, importlib, traceback, math, collections
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
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing")
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    h = conns[0]["h"]; hx, hy = h.x, h.y
    planes = collections.defaultdict(list)
    for t in range(sb.gs("get_num_triangle_i_ds")(dyn)):
        vs = sb._tri_positions(dyn, t)
        if not vs: continue
        nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        if nrm.length() < 1e-4: continue
        nn = nrm.normal()
        if abs(nn.z) > 0.2 or abs(nn.x * -hy + nn.y * hx) < 0.95: continue
        sides = [-v.x * hy + v.y * hx for v in vs]
        if max(sides) - min(sides) > 2.0: continue
        tside = round(sum(sides) / 3.0)
        if abs(abs(tside) - 120) > 3 and abs(abs(tside) - 60) > 3: continue
        r = sb.gs("get_triangle_u_vs")(dyn, 0, t)
        uvs = [u for u in r if isinstance(u, unreal.Vector2D)] if isinstance(r, tuple) else []
        if len(uvs) != 3: continue
        planes[tside].append((t, [(v.x * hx + v.y * hy, v.z, u.x * 64, u.y * 64) for v, u in zip(vs, uvs)]))
    for tside, faces in sorted(planes.items()):
        pts = [(a, u) for _, vv in faces for (a, z, u, v) in vv]
        # robust line: slope from median of pairwise over a sample, intercept median
        pts.sort()
        n = len(pts)
        slopes = []
        for i in range(0, n, max(1, n // 60)):
            for j in range(i + 1, n, max(1, n // 60)):
                if abs(pts[j][0] - pts[i][0]) > 20: slopes.append((pts[j][1] - pts[i][1]) / (pts[j][0] - pts[i][0]))
        slopes.sort(); B = slopes[len(slopes) // 2] if slopes else 0.0
        ints = sorted(u - B * a for a, u in pts); A = ints[len(ints) // 2]
        off = [(t, vv) for t, vv in faces if any(abs(u - (A + B * a)) > 0.05 for (a, z, u, v) in vv)]
        amin = min(a for a, _ in pts); amax = max(a for a, _ in pts)
        out.append("plane t=%d (arm0 frame): %d faces, along %.0f..%.0f, line u = %.3f + %.5f*s px; off-line faces: %d" % (tside, len(faces), amin, amax, A, B, len(off)))
        for t, vv in off[:25]:
            out.append("   tri %d: %s" % (t, [(round(a, 1), round(z, 1), round(u - (A + B * a), 2)) for (a, z, u, v) in vv]))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump270.txt", "w", encoding="utf-8").write("\n".join(out))
