import unreal, collections
out = []
GA, GQ = unreal.GeometryScript_AssetUtils, unreal.GeometryScript_MeshQueries
def tuv(dm, ch, t): return [x for x in GQ.get_triangle_u_vs(dm, ch, t) if isinstance(x, unreal.Vector2D)]
try:
    for n in ('SM_Towers_Towers_114', 'SM_Towers_Towers_03', 'SM_Towers_Towers_135'):
        sm = unreal.load_asset('/Game/Houses/Meshes/' + n)
        dm = unreal.DynamicMesh()
        GA.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
        seen = collections.Counter()
        for t in range(GQ.get_num_triangle_i_ds(dm)):
            u1, u3, u4 = tuv(dm, 1, t), tuv(dm, 3, t), tuv(dm, 4, t)
            if not u1 or abs((1 - u1[0].y) - 1) > 0.5: continue          # walls only
            c0, c1, c2 = round(u3[0].x), round(1 - u3[0].y), round(u4[0].x)
            wn = max(round(1 - u4[0].y), 1)
            seen[(c0, c1, c2, wn)] += 1
        for (c0, c1, c2, wn), k in seen.items():
            cov = []
            for slot in range(18):
                ch = slot // 6; s6 = slot % 6
                cv = (c0, c1, c2)[ch]
                cov.append((cv >> (3 * s6)) & 7)
            out.append("%s: %d wall tris, tiles on wall %d, cover per 1/18 of the wall (floors hidden): %s" % (n, k, wn, cov))
except Exception:
    import traceback; out.append(traceback.format_exc()[-1200:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump355.txt", "w").write("\n".join(out))
