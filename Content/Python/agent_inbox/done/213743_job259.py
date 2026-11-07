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
    for k, c in enumerate(conns):
        out.append("arm %d h(%.2f,%.2f) lead %.0f s_start %.0f mirror %s" % (k, c["h"].x, c["h"].y, c["lead"], sb.CROSSING_HUB + c["lead"], c.get("mirror")))
    out.append("mitres %s" % {k: tuple((round(p[0]), round(p[1])) for p in v[:2]) for k, v in sb._crossing_mitres(conns).items()})
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing")
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    N = 64.0
    hits = collections.defaultdict(list)
    for t in range(sb.gs("get_num_triangle_i_ds")(dyn)):
        vs = sb._tri_positions(dyn, t)
        if not vs: continue
        nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        if nrm.length() < 1e-6: continue
        nn = nrm.normal()
        if abs(nn.z) > 0.2: continue
        r = sb.gs("get_triangle_u_vs")(dyn, 0, t)
        uvs = [u for u in r if isinstance(u, unreal.Vector2D)] if isinstance(r, tuple) else []
        if len(uvs) != 3: continue
        for i in range(3):
            j = (i + 1) % 3
            a, b = vs[i], vs[j]
            if math.hypot(a.x - b.x, a.y - b.y) > 0.5 or abs(a.z - b.z) < 5: continue   # vertical edges only
            for (v, u) in ((a, uvs[i]), (b, uvs[j])):
                px = u.x * N
                fr = abs(px - round(px))
                key = (round(v.x / 2) * 2, round(v.y / 2) * 2)
                hits[key].append(round(fr, 2))
    bad = []
    for key, frs in hits.items():
        m = max(frs)
        if m > 0.08:
            bad.append((m, key, sorted(set(frs))[:6]))
    bad.sort(reverse=True)
    out.append("vertical texture edges ending mid-pixel: %d spots" % len(bad))
    for m, key, frs in bad[:60]:
        x, y = key
        desc = []
        for k, c in enumerate(conns):
            hx, hy = c["h"].x, c["h"].y
            desc.append("a%d s%.0f t%.0f" % (k, x * hx + y * hy, -x * hy + y * hx))
        out.append("  (%5.0f,%5.0f) worst %.2f px  fracs %s | %s" % (x, y, m, frs, '; '.join(desc)))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump259.txt", "w", encoding="utf-8").write("\n".join(out))
