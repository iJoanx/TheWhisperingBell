import unreal, collections, math
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump356.txt", "w").write("\n".join(out))
GA, GQ = unreal.GeometryScript_AssetUtils, unreal.GeometryScript_MeshQueries
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
def tuv(dm, ch, t): return [x for x in GQ.get_triangle_u_vs(dm, ch, t) if isinstance(x, unreal.Vector2D)]
def tpos(dm, t): return [x for x in GQ.get_triangle_positions(dm, t) if isinstance(x, unreal.Vector)]
# ---- 1) towers: full precision UVs
try:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    names = sorted(str(x.asset_name) for x in ar.get_assets_by_path('/Game/Houses/Meshes', recursive=True) if str(x.asset_name).startswith('SM_Towers'))
    before = collections.Counter(); changed = 0
    for n in names:
        sm = unreal.load_asset('/Game/Houses/Meshes/' + n)
        bs = SMES.get_lod_build_settings(sm, 0)
        fp = bs.get_editor_property('use_full_precision_u_vs')
        before[fp] += 1
        if not fp:
            bs.set_editor_property('use_full_precision_u_vs', True)
            SMES.set_lod_build_settings(sm, 0, bs)
            changed += 1
    out.append("towers full-precision UVs before: %s; switched on for %d" % (dict(before), changed))
    h = unreal.load_asset('/Game/Houses/Meshes/SM_Houses_00')
    out.append("(a house, for comparison: full precision = %s)" % SMES.get_lod_build_settings(h, 0).get_editor_property('use_full_precision_u_vs'))
except Exception:
    import traceback; out.append(traceback.format_exc()[-1000:])
dump()
# ---- 2) house 6187: find the chimneys, which one floats
try:
    sm = unreal.load_asset('/Game/Houses/Meshes/SM_Houses_6187')
    dm = unreal.DynamicMesh()
    GA.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    n = GQ.get_num_triangle_i_ds(dm)
    tris = {}
    for t in range(n):
        p = tpos(dm, t); u1 = tuv(dm, 1, t)
        if len(p) == 3 and u1: tris[t] = (p, round(1 - u1[0].y))
    out.append("house 6187: %d tris, classes %s" % (n, dict(collections.Counter(c for _, c in tris.values()))))
    chim = [t for t, (p, c) in tris.items() if c in (4, 5)]
    # group chimney tris into pieces by shared vertex positions
    key = lambda v: (round(v.x, 1), round(v.y, 1), round(v.z, 1))
    parent = {t: t for t in chim}
    def f(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    owner = {}
    for t in chim:
        for v in tris[t][0]:
            k = key(v)
            if k in owner: parent[f(t)] = f(owner[k])
            else: owner[k] = t
    groups = collections.defaultdict(list)
    for t in chim: groups[f(t)].append(t)
    roof = [t for t, (p, c) in tris.items() if c not in (1, 2, 3, 4, 5)]
    def roof_z(x, y):
        best = None
        for t in roof:
            a, b, c = tris[t][0]
            d = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y)
            if abs(d) < 1e-6: continue
            l1 = ((b.y - c.y) * (x - c.x) + (c.x - b.x) * (y - c.y)) / d
            l2 = ((c.y - a.y) * (x - c.x) + (a.x - c.x) * (y - c.y)) / d
            l3 = 1 - l1 - l2
            if min(l1, l2, l3) >= -1e-4:
                z = l1 * a.z + l2 * b.z + l3 * c.z
                best = z if best is None else max(best, z)
        return best
    floating = []
    for g, ts in groups.items():
        vs = [v for t in ts for v in tris[t][0]]
        cx = sum(v.x for v in vs) / len(vs); cy = sum(v.y for v in vs) / len(vs)
        zmin = min(v.z for v in vs); zmax = max(v.z for v in vs)
        # roof height under each bottom corner of the chimney
        bottoms = [v for v in vs if v.z < zmin + 1]
        rz = [roof_z(v.x, v.y) for v in bottoms]
        rz = [z for z in rz if z is not None]
        gap = (zmin - max(rz)) if rz else None
        out.append("  chimney piece: %d tris, centre (%.0f, %.0f), z %.0f..%.0f, roof under its base %s, gap %s" % (
            len(ts), cx, cy, zmin, zmax, [round(z) for z in rz][:6], None if gap is None else round(gap, 1)))
        if gap is None or gap > 5: floating.append(ts)
    out.append("floating chimneys: %d" % len(floating))
    if len(floating) == 1:
        il = unreal.GeometryScript_List.convert_array_to_index_list(floating[0], unreal.GeometryScriptIndexType.TRIANGLE)
        unreal.GeometryScript_MeshBasicEdits.delete_triangles_from_mesh(dm, il, True)
        opts = unreal.GeometryScriptCopyMeshToAssetOptions()
        for p_, v_ in (('enable_recompute_normals', False), ('enable_recompute_tangents', False), ('enable_remove_degenerates', False), ('replace_materials', False)):
            try: opts.set_editor_property(p_, v_)
            except Exception: pass
        GA.copy_mesh_to_static_mesh(dm, sm, opts, unreal.GeometryScriptMeshWriteLOD())
        chk = unreal.DynamicMesh()
        GA.copy_mesh_from_static_mesh(sm, chk, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
        out.append("deleted it: %d -> %d tris" % (n, GQ.get_num_triangle_i_ds(chk)))
    else:
        out.append("not deleting anything (expected exactly one floating chimney)")
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
