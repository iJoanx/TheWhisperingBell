import unreal, collections
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump338.txt", "w", encoding="utf-8").write("\n".join(out))
try:
    SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    MEL = unreal.MaterialEditingLibrary
    m = unreal.load_asset('/Game/Houses/M_Houses_Master')
    try:
        exprs = []
        for prop in (unreal.MaterialProperty.MP_BASE_COLOR, unreal.MaterialProperty.MP_EMISSIVE_COLOR):
            e = MEL.get_material_property_input_node(m, prop)
            exprs.append((str(prop), e.get_class().get_name() if e else None))
        out.append("material inputs: %s" % exprs)
        seen, stack, cls = set(), [MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)], collections.Counter()
        while stack:
            e = stack.pop()
            if e is None or e.get_path_name() in seen: continue
            seen.add(e.get_path_name())
            d = e.get_class().get_name()
            extra = ''
            for p in ('coordinate_index', 'parameter_name', 'texture'):
                try: extra += ' %s=%s' % (p, e.get_editor_property(p))
                except Exception: pass
            out.append("  expr %s%s" % (d, extra[:200]))
            for i in MEL.get_inputs_for_material_expression(m, e): stack.append(i)
    except Exception as ex: out.append("mat err " + str(ex)[:300])
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    assets = ar.get_assets_by_path('/Game/Houses/Meshes', recursive=True)
    names = sorted(str(a.asset_name) for a in assets if str(a.asset_name).startswith('SM_Towers'))
    out.append("tower meshes: %d" % len(names))
    def info(n):
        sm = unreal.load_asset('/Game/Houses/Meshes/' + n)
        uv = sm.get_num_uv_channels(0)
        try: vc = SMES.has_vertex_colors(sm)
        except Exception as e: vc = 'err'
        try: inst = SMES.has_instance_vertex_colors(sm)
        except Exception: inst = '?'
        return (n, uv, vc, sm.get_num_sections(0))
    rows = [info(n) for n in names]
    cnt = collections.Counter((r[1], r[2]) for r in rows)
    out.append("towers by (uv channels, vertex colors): %s" % dict(cnt))
    for r in rows: out.append("  %s uv=%s vcol=%s sections=%s" % r)
    houses = sorted(str(a.asset_name) for a in assets if str(a.asset_name).startswith('SM_House'))[:200:20]
    for n in houses: out.append("  HOUSE %s uv=%s vcol=%s sections=%s" % info(n))
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
