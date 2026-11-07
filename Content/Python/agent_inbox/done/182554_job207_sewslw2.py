import unreal, traceback
out = []
MEL = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
try:
    src = '/Game/Sewers/Materials/M_SewerWaterFlowV2'
    dst = '/Game/Water/M_SewerWaterFlow_SLW'
    if eal.does_asset_exist(dst): eal.delete_asset(dst)
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
    mi = unreal.load_asset('/Game/Sewers/Materials/MI_SewerWaterV2_Opaque')
    mi.set_editor_property('parent', m)
    MEL.set_material_instance_vector_parameter_value(mi, 'WaterColor', unreal.LinearColor(0.05, 0.055, 0.015, 1))
    MEL.set_material_instance_vector_parameter_value(mi, 'RippleColor', unreal.LinearColor(0.12, 0.13, 0.05, 1))
    MEL.update_material_instance(mi)
    out.append("MI parent: %s  WaterColor=%s RippleColor=%s two-sided=%s" % (mi.get_editor_property('parent').get_path_name(),
        MEL.get_material_instance_vector_parameter_value(mi, 'WaterColor'), MEL.get_material_instance_vector_parameter_value(mi, 'RippleColor'),
        mi.get_editor_property('base_property_overrides').get_editor_property('two_sided')))
    old = '/Game/Water/M_SewageWater_SLW'
    if eal.does_asset_exist(old): out.append("removed simple first attempt: %s" % eal.delete_asset(old))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump207.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
