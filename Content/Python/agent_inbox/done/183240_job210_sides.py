import unreal, traceback
out = []
MEL = unreal.MaterialEditingLibrary
try:
    m = unreal.load_asset('/Game/Water/M_SewerWaterFlow_SLW')
    prev = MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_OPACITY)
    out.append("opacity was driven by: %s" % (prev.get_class().get_name() if prev else None))
    X = lambda cls, x, y: MEL.create_material_expression(m, cls, x, y)
    C = MEL.connect_material_expressions
    # Single Layer Water's Opacity: 1 = solid surface lit with Base Color, 0 = water.
    # TwoSidedSign is +1 on the top (front) face and -1 on the underside.
    tss = X(unreal.MaterialExpressionTwoSidedSign, -700, 1400)
    sat = X(unreal.MaterialExpressionSaturate, -550, 1400); C(tss, '', sat, '')
    top = X(unreal.MaterialExpressionScalarParameter, -700, 1500); top.set_editor_property('parameter_name', 'TopOpacity'); top.set_editor_property('default_value', 1.0)
    bot = X(unreal.MaterialExpressionScalarParameter, -700, 1600); bot.set_editor_property('parameter_name', 'UndersideOpacity'); bot.set_editor_property('default_value', 0.0)
    lerp = X(unreal.MaterialExpressionLinearInterpolate, -350, 1450)
    C(bot, '', lerp, 'A'); C(top, '', lerp, 'B'); C(sat, '', lerp, 'Alpha')
    MEL.connect_material_property(lerp, '', unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(m)
    now = MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_OPACITY)
    out.append("opacity now driven by: %s; expressions=%d" % (now.get_class().get_name() if now else None, MEL.get_num_material_expressions(m)))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump210.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
