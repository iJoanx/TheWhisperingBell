import sys, importlib, traceback, math, collections
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    nodes = [a for a in sb._actors() if sb._is_node(a)]
    _, per = sb._gather(nodes, [])
    nd = [a for a in nodes if a.get_actor_label() == "SL_305_Crossing"][0]
    conns = sb._local_conns(nd, per[nd.get_path_name()])
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_305_Crossing")
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    hx, hy = conns[0]["h"].x, conns[0]["h"].y
    # 1. walkway faces (upward, |z|<15), grouped by side of arm0's line; u-seams at shared vertices
    hits = collections.defaultdict(list)
    vhits = collections.defaultdict(list)
    for t in range(sb.gs("get_num_triangle_i_ds")(dyn)):
        vs = sb._tri_positions(dyn, t)
        if not vs: continue
        nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        if nrm.length() < 1e-4: continue
        nn = nrm.normal()
        r = sb.gs("get_triangle_u_vs")(dyn, 0, t)
        uvs = [u for u in r if isinstance(u, unreal.Vector2D)] if isinstance(r, tuple) else []
        if len(uvs) != 3: continue
        if abs(nn.z) < 0.2 and min(v.z for v in vs) > -101 and max(v.z for v in vs) < 1:
            for v, u in zip(vs, uvs):
                hits[(round(v.x, 1), round(v.y, 1), round(v.z, 1))].append((round(u.x * 64, 2), round(u.y * 64, 2), t))
        if min(v.z for v in vs) > 245:
            for v, u in zip(vs, uvs):
                vhits[(round(v.x, 1), round(v.y, 1), round(v.z, 1))].append((round(u.x * 64, 2), round(u.y * 64, 2), t))
    def report(name, H, n=40):
        bad = []
        for key, lst in H.items():
            us = sorted(set((a, b) for a, b, _ in lst if not (abs(a - 0.25) < 0.01 and abs(b - 63.75) < 0.01)))
            if len(us) < 2: continue
            du = max(abs(((p[0] - us[0][0]) + 32) % 64 - 32) for p in us)
            dv = max(abs(((p[1] - us[0][1]) + 32) % 64 - 32) for p in us)
            if (0.05 < du < 3.0 and dv < 3.0) or (0.05 < dv < 3.0 and du < 3.0):
                a0 = key[0] * hx + key[1] * hy; t0 = -key[0] * hy + key[1] * hx
                bad.append((max(du, dv), key, round(a0), round(t0), us[:5], sorted(set(x[2] for x in lst))[:6]))
        bad.sort(reverse=True)
        out.append("== %s: %d seam vertices" % (name, len(bad)))
        for b in bad[:n]:
            out.append("   d%.2f at %s (arm0 s%d t%d) uv px %s tris %s" % b)
    # also list faces on the channel walls with their vertices, for the worst spot

    report("channel walls (vertical, -100..0)", hits)
    report("vault (z>245)", vhits)
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump297.txt", "w", encoding="utf-8").write("\n".join(out))
