import unreal, collections
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump340.txt", "w", encoding="utf-8").write("\n".join(out))
GS = unreal
def uv5(sm):
    dm = unreal.DynamicMesh()
    r = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    vals = collections.Counter()
    n = unreal.GeometryScript_MeshQueries.get_num_triangle_i_ds(dm)
    for t in range(0, n, max(1, n // 40)):
        res = unreal.GeometryScript_MeshQueries.get_triangle_u_vs(dm, 5, t)
        uvs = [x for x in res if isinstance(x, unreal.Vector2D)]
        if uvs: vals[round(uvs[0].x, 2)] += 1
    return vals
try:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    assets = ar.get_assets_by_path('/Game/Houses/Meshes', recursive=True)
    names = sorted(str(a.asset_name) for a in assets if str(a.asset_name).startswith('SM_Towers'))
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    loc = {}
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.StaticMeshActor):
            sm = a.static_mesh_component.static_mesh
            if sm and sm.get_name().startswith('SM_Towers'):
                loc[sm.get_name()] = a.get_actor_location()
    bad, good = [], []
    for n in names:
        sm = unreal.load_asset('/Game/Houses/Meshes/' + n)
        v = uv5(sm)
        code = v.most_common(1)[0][0] if v else None
        ward = None if code is None else (int(round(code)) % 16) - 1
        l = loc.get(n)
        row = "%s code=%s ward=%s set=%s mixed=%s at %s" % (n, code, ward, None if code is None else int(round(code)) // 16, len(v) > 1,
              "(%.0f, %.0f)" % (l.x, l.y) if l else "not placed")
        (bad if ward is None or ward < 0 else good).append(row)
    out.append("towers WITHOUT ward: %d / %d" % (len(bad), len(names)))
    out += ["  " + r for r in bad]
    out.append("towers with ward: %d" % len(good))
    out += ["  " + r for r in good[:200]]
    # a few houses for comparison
    hs = sorted(str(a.asset_name) for a in assets if str(a.asset_name).startswith('SM_Houses'))
    nh = 0
    for n in hs[::max(1, len(hs) // 300)]:
        v = uv5(unreal.load_asset('/Game/Houses/Meshes/' + n))
        code = v.most_common(1)[0][0] if v else None
        if code is None or int(round(code)) % 16 == 0: nh += 1
    out.append("sampled %d houses: %d without ward" % (len(hs[::max(1, len(hs) // 300)]), nh))
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
