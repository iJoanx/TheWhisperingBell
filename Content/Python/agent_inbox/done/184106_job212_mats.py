import unreal, traceback
out = []
MEL = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
try:
    orig = unreal.load_asset('/Game/Sewers/Materials/M_SewerWaterFlowV2')
    slw = unreal.load_asset('/Game/Water/M_SewerWaterFlow_SLW')
    # ---- A) put the water copy's opacity back the way it was before the top/underside switch
    o_node = MEL.get_material_property_input_node(orig, unreal.MaterialProperty.MP_OPACITY)
    ox, oy = o_node.get_editor_property('material_expression_editor_x'), o_node.get_editor_property('material_expression_editor_y')
    pref = slw.get_path_name()
    live = [e for e in unreal.ObjectIterator(unreal.MaterialExpression)
            if e.get_path_name().startswith(pref) and unreal.SystemLibrary.is_valid(e)]
    old_lerp = next((e for e in live if isinstance(e, unreal.MaterialExpressionLinearInterpolate)
                     and e.get_editor_property('material_expression_editor_x') == ox and e.get_editor_property('material_expression_editor_y') == oy), None)
    out.append("original opacity node at (%d,%d), found in copy: %s" % (ox, oy, old_lerp is not None))
    mine = [e for e in live if isinstance(e, (unreal.MaterialExpressionTwoSidedSign, unreal.MaterialExpressionSaturate))
            or (isinstance(e, unreal.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name')) in ('TopOpacity', 'UndersideOpacity'))
            or (isinstance(e, unreal.MaterialExpressionLinearInterpolate) and e.get_editor_property('material_expression_editor_x') == -350 and e.get_editor_property('material_expression_editor_y') == 1450)]
    if old_lerp is not None:
        for e in mine: MEL.delete_material_expression(slw, e)
        MEL.connect_material_property(old_lerp, '', unreal.MaterialProperty.MP_OPACITY)
        MEL.recompile_material(slw)
        out.append("removed %d top/underside nodes, opacity reconnected; expressions=%d" % (len(mine), MEL.get_num_material_expressions(slw)))
    # ---- B) top: original opaque flow material, one-sided
    top = unreal.load_asset('/Game/Sewers/Materials/MI_SewerWaterV2_Opaque')
    vec_overrides = {}
    for n in [str(x) for x in MEL.get_vector_parameter_names(orig)]:
        vec_overrides[n] = MEL.get_material_instance_vector_parameter_value(top, n)
    sca = {str(n): MEL.get_material_instance_scalar_parameter_value(top, n) for n in MEL.get_scalar_parameter_names(orig)}
    tex = {str(n): MEL.get_material_instance_texture_parameter_value(top, n) for n in MEL.get_texture_parameter_names(orig)}
    top.set_editor_property('parent', orig)
    o = top.get_editor_property('base_property_overrides')
    o.set_editor_property('override_two_sided', False); o.set_editor_property('two_sided', False)
    top.set_editor_property('base_property_overrides', o)
    for n in ('WaterColor', 'RippleColor'):   # back to the material's own colours
        MEL.set_material_instance_vector_parameter_value(top, n, MEL.get_material_default_vector_parameter_value(orig, n))
    MEL.update_material_instance(top)
    out.append("top MI parent=%s two_sided_override=%s WaterColor=%s" % (top.get_editor_property('parent').get_name(),
               top.get_editor_property('base_property_overrides').get_editor_property('override_two_sided'),
               MEL.get_material_instance_vector_parameter_value(top, 'WaterColor')))
    # ---- C) underside instance: the Single Layer Water copy with the same flow settings, murky colours, one-sided
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
    out.append("underside MI parent=%s, copied %d scalar + %d texture settings" % (und.get_editor_property('parent').get_name(), len(sca), len([v for v in tex.values() if v])))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump212.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
