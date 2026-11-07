import sys, importlib, traceback, math, collections
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    def load(path):
        sm = unreal.load_asset(path)
        dyn = unreal.DynamicMesh()
        read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
        dyn, _ = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
        return dyn
    def vscan(dyn, name, inside=None):
        hits = collections.defaultdict(list)
        for t in range(sb.gs("get_num_triangle_i_ds")(dyn)):
            vs = sb._tri_positions(dyn, t)
            if not vs: continue
            nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
            if nrm.length() < 1e-4: continue
            r = sb.gs("get_triangle_u_vs")(dyn, 0, t)
            uvs = [u for u in r if isinstance(u, unreal.Vector2D)] if isinstance(r, tuple) else []
            c1 = sb.gs("get_triangle_u_vs")(dyn, 1, t)
            cell = [u for u in c1 if isinstance(u, unreal.Vector2D)] if isinstance(c1, tuple) else []
            cell = (round(cell[0].x, 3), round(cell[0].y, 3)) if cell else None
            if len(uvs) != 3: continue
            for v, u in zip(vs, uvs):
                if inside and not inside(v): continue
                hits[(round(v.x, 1), round(v.y, 1), round(v.z, 1))].append((cell, u.y * 64))
        seams = collections.Counter(); halfs = collections.Counter(); ex = {}
        for key, lst in hits.items():
            by = collections.defaultdict(set)
            for cell, vp in lst: by[cell].add(round(vp, 2))
            for cell, vals in by.items():
                vals = sorted(vals)
                if len(vals) > 1 and any(abs(((x - vals[0]) + 32) % 64 - 32) > 0.05 for x in vals):
                    zb = round(key[2] / 10) * 10
                    seams[zb] += 1
                    if zb not in ex: ex[zb] = (key, cell, vals[:5])
                for x in vals:
                    if abs(x - round(x)) > 0.1:
                        halfs[round(key[2] / 10) * 10] += 1
                        break
        out.append("== %s: vertices where faces of the same texture cell disagree in V (by height, cm): %s" % (name, sorted(seams.items())))
        for zb, e in sorted(ex.items()): out.append("     e.g. z~%s at %s cell %s V px %s" % (zb, e[0], e[1], e[2]))
        out.append("   vertices with V off the pixel grid (by height): %s" % sorted(halfs.items()))
    vscan(load("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing"), "SL_303 crossing", inside=lambda v: v.z > -101 and v.z < 380)
    for pt in sb.PASSAGE_TYPES:
        try:
            vscan(load(sb.PASSAGE_TYPES[pt]["mesh"]), "passage mesh %s" % pt)
        except Exception as e:
            out.append("passage %s: %s" % (pt, e))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump277.txt", "w", encoding="utf-8").write("\n".join(out))
