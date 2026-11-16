import unreal
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump360.txt", "w").write("\n".join(out))
MEL = unreal.MaterialEditingLibrary
try:
    m = unreal.load_asset('/Game/Houses/M_Houses_Master')
    seen, stack, cust = set(), [MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)], None
    while stack:
        e = stack.pop()
        if e is None or e.get_path_name() in seen: continue
        seen.add(e.get_path_name())
        if e.get_class().get_name() == 'MaterialExpressionCustom': cust = e; break
        stack += list(MEL.get_inputs_for_material_expression(m, e))
    code = str(cust.get_editor_property('code'))
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\houses_custom_backup360.hlsl", "w").write(code)
    A_OLD = "&& uvm.x > 1.0 - GreenStripWidth)"
    A_NEW = "&& floor(saturate(qm.x) * 64.0) >= 64.0 - floor(GreenStripWidth * 64.0 + 0.5))   // whole texels of the 64 px image"
    B_OLD = "// the colour image, then the tint"
    B_NEW = """// roof undersides (eaves): one flat colour, the centre of the Tiles image's bottom-left texel, so no texel edge runs through them
if (abs(slotI - 13.0) < 0.5 && Nrm.z < -0.5)
    qS = float2(0.5 / 64.0, 63.5 / 64.0);

// the colour image, then the tint"""
    for o in (A_OLD, B_OLD):
        if code.count(o) != 1: raise Exception("expected one match for %r, found %d" % (o, code.count(o)))
    code = code.replace(A_OLD, A_NEW).replace(B_OLD, B_NEW)
    ins = list(cust.get_editor_property('inputs'))
    if 'Nrm' not in [str(i.get_editor_property('input_name')) for i in ins]:
        ci = unreal.CustomInput(); ci.set_editor_property('input_name', 'Nrm'); ins.append(ci)
        cust.set_editor_property('inputs', ins)
    cust.set_editor_property('code', code)
    n = MEL.create_material_expression(m, unreal.MaterialExpressionVertexNormalWS, cust.get_editor_property('material_expression_editor_x') - 400, cust.get_editor_property('material_expression_editor_y') + 1000)
    out.append("connected Nrm: %s" % MEL.connect_material_expressions(n, '', cust, 'Nrm'))
    MEL.recompile_material(m)
    c2 = str(cust.get_editor_property('code'))
    out.append("pixel cut in: %s; eave block in: %s" % (A_NEW in c2, 'Nrm.z < -0.5' in c2))
    out.append("recompiled (not saved)")
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
