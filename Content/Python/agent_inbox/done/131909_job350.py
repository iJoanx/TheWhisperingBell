import unreal, collections
out = []
GA, GQ = unreal.GeometryScript_AssetUtils, unreal.GeometryScript_MeshQueries
try:
    m = unreal.load_asset('/Game/Houses/M_Houses_Master')
    for p in ('NumWards', 'SetsPerWard', 'ColourStride', 'MaskStride', 'TintStrength', 'EdgeInset'):
        out.append("%s = %s" % (p, unreal.MaterialEditingLibrary.get_material_default_scalar_parameter_value(m, p)))
    for a in ('HouseArray', 'MaskArray'):
        t = unreal.load_asset('/Game/Houses/' + a)
        for p in ('source_textures',):
            try: out.append("%s slices %d" % (a, len(t.get_editor_property(p))))
            except Exception as e: out.append("%s %s" % (a, str(e)[:120]))
    # every tower: code, special on foundation
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    names = sorted(str(x.asset_name) for x in ar.get_assets_by_path('/Game/Houses/Meshes', recursive=True) if str(x.asset_name).startswith('SM_Towers'))
    for n in names:
        sm = unreal.load_asset('/Game/Houses/Meshes/' + n)
        dm = unreal.DynamicMesh()
        GA.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
        sp, code = collections.Counter(), None
        for t in range(GQ.get_num_triangle_i_ds(dm)):
            u1 = [x for x in GQ.get_triangle_u_vs(dm, 1, t) if isinstance(x, unreal.Vector2D)]
            if u1 and abs((1 - u1[0].y) - 2) < 0.5: sp[round(u1[0].x)] += 1
            if code is None:
                u5 = [x for x in GQ.get_triangle_u_vs(dm, 5, t) if isinstance(x, unreal.Vector2D)]
                if u5: code = int(round(u5[0].x))
        out.append("%s code %s ward %s set %s foundation-special %s" % (n, code, code % 16 - 1, code // 16, dict(sp)))
except Exception:
    import traceback; out.append(traceback.format_exc()[-1200:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump350.txt", "w").write("\n".join(out))
