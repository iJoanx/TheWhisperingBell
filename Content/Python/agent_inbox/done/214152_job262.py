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
    N = 64.0

    def scan(dyn):
        hits = collections.defaultdict(list)
        for t in range(sb.gs("get_num_triangle_i_ds")(dyn)):
            vs = sb._tri_positions(dyn, t)
            if not vs: continue
            nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
            if nrm.length() < 1e-6: continue
            if abs(nrm.normal().z) > 0.2: continue
            r = sb.gs("get_triangle_u_vs")(dyn, 0, t)
            uvs = [u for u in r if isinstance(u, unreal.Vector2D)] if isinstance(r, tuple) else []
            if len(uvs) != 3: continue
            for i in range(3):
                j = (i + 1) % 3
                a, b = vs[i], vs[j]
                if math.hypot(a.x - b.x, a.y - b.y) > 0.5 or abs(a.z - b.z) < 5: continue
                for (v, u) in ((a, uvs[i]), (b, uvs[j])):
                    hits[(round(v.x / 2) * 2, round(v.y / 2) * 2)].append(u.x * N)
        rows = []
        for key, pxs in hits.items():
            if not any(abs(-key[0] * c["h"].y + key[1] * c["h"].x) <= 123 and key[0] * c["h"].x + key[1] * c["h"].y >= -5 for c in conns):
                continue
            vals = sorted(set(round(p, 2) for p in pxs))
            if not any(abs(((p - vals[0]) + 32) % 64 - 32) > 0.05 for p in vals): continue
            m = max(abs(p - round(p)) for p in vals)
            if m > 0.08:
                desc = '; '.join("a%d s%.0f t%.0f" % (k, key[0] * c["h"].x + key[1] * c["h"].y, -key[0] * c["h"].y + key[1] * c["h"].x) for k, c in enumerate(conns))
                rows.append((m, "  (%5.0f,%5.0f) worst %.2f px  px-values %s | %s" % (key[0], key[1], m, vals[:6], desc)))
        rows.sort(reverse=True)
        out.append("interior vertical seams mid-pixel: %d" % len(rows))
        out.extend([r for _, r in rows[:40]])

    for fit in (False, True):
        sb.FIT_WALLS_TO_PIXELS = fit
        sb._UV_TABLES.clear(); sb._OUTER.clear(); del sb._SLOTS[:]
        dyn = sb._build_node_mesh(nd, per[nd.get_path_name()])
        out.append("===== FIT %s ===== %s" % (fit, sb.FIT_STATS))
        scan(dyn)
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump262.txt", "w", encoding="utf-8").write("\n".join(out))
