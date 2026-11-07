import unreal, traceback
out = []
MEL = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
try:
    top = unreal.load_asset('/Game/Sewers/Materials/MI_SewerWaterV2_Opaque')
    out.append("top MI parent on load: %s" % (top.get_editor_property('parent').get_path_name() if top.get_editor_property('parent') else None))
    src = '/Game/Sewers/Materials/M_SewerWaterFlowV2'
    dst = '/Game/Water/M_SewerWaterFlow_SLW'
    if eal.does_asset_exist(dst): raise RuntimeError('copy already exists')
    m = eal.duplicate_asset(src, dst)
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('two_sided', True)
    X = lambda cls, x, y: MEL.create_material_expression(m, cls, x, y)
    def vparam(n, v, x, y):
        e = X(unreal.MaterialExpressionVectorParameter, x, y); e.set_editor_property('parameter_name', n); e.set_editor_property('default_value', unreal.LinearColor(*v)); return e
    def sparam(n, v, x, y):
        e = X(unreal.MaterialExpressionScalarParameter, x, y); e.set_editor_property('parameter_name', n); e.set_editor_property('default_value', v); return e
    wo = X(unreal.MaterialExpressionSingleLayerWaterMaterialOutput, 600, 900)
    for e, pin in ((vparam('ScatteringCoefficients', (0.10, 0.11, 0.03, 1), 200, 850), 'Scattering Coefficients'),
                   (vparam('AbsorptionCoefficients', (1.2, 1.0, 2.5, 1), 200, 1000), 'Absorption Coefficients'),
                   (sparam('PhaseG', 0.2, 200, 1150), 'PhaseG'),
                   (sparam('ColorScaleBehindWater', 0.35, 200, 1250), 'ColorScaleBehindWater')):
        try: MEL.connect_material_expressions(e, '', wo, pin)
        except Exception as ex: out.append("connect %s failed: %s" % (pin, ex))
    MEL.recompile_material(m)
    out.append("built %s (%d expressions, shading=%s)" % (dst, MEL.get_num_material_expressions(m), m.get_editor_property('shading_model')))
    orig = unreal.load_asset('/Game/Sewers/Materials/M_SewerWaterFlowV2')
    slw = m
    # ---- top: original opaque flow material, one-sided
    top.set_editor_property('parent', orig)
    o = top.get_editor_property('base_property_overrides')
    o.set_editor_property('override_two_sided', False); o.set_editor_property('two_sided', False)
    top.set_editor_property('base_property_overrides', o)
    sca, tex = {}, {}
    for n in MEL.get_scalar_parameter_names(orig):
        try: sca[str(n)] = MEL.get_material_instance_scalar_parameter_value(top, n)
        except Exception: pass
    for n in MEL.get_texture_parameter_names(orig):
        try: tex[str(n)] = MEL.get_material_instance_texture_parameter_value(top, n)
        except Exception: pass
    for n in ('WaterColor', 'RippleColor'):
        MEL.set_material_instance_vector_parameter_value(top, n, MEL.get_material_default_vector_parameter_value(orig, n))
    MEL.update_material_instance(top)
    out.append("top MI parent=%s two_sided_override=%s WaterColor=%s" % (top.get_editor_property('parent').get_name(),
               top.get_editor_property('base_property_overrides').get_editor_property('override_two_sided'),
               MEL.get_material_instance_vector_parameter_value(top, 'WaterColor')))
    # ---- underside instance
    up = '/Game/Water/MI_SewerWater_Underside'
    und = unreal.load_asset(up) if eal.does_asset_exist(up) else at.create_asset('MI_SewerWater_Underside', '/Game/Water', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    und.set_editor_property('parent', slw)
    for n, v in sca.items():
        try: MEL.set_material_instance_scalar_parameter_value(und, n, v)
        except Exception: pass
    for n, v in tex.items():
        try:
            if v: MEL.set_material_instance_texture_parameter_value(und, n, v)
        except Exception: pass
    MEL.set_material_instance_vector_parameter_value(und, 'WaterColor', unreal.LinearColor(0.05, 0.055, 0.015, 1))
    MEL.set_material_instance_vector_parameter_value(und, 'RippleColor', unreal.LinearColor(0.12, 0.13, 0.05, 1))
    MEL.update_material_instance(und)
    out.append("underside MI parent=%s, copied %d scalar + %d texture settings: %s" % (und.get_editor_property('parent').get_name(), len(sca), len([v for v in tex.values() if v]), sca))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump214.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
