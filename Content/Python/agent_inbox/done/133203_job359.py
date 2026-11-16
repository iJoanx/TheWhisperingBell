import unreal
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump359.txt", "w").write("\n".join(out))
MEL = unreal.MaterialEditingLibrary
try:
    m = unreal.load_asset('/Game/Houses/M_Houses_Master')
    # find the Custom node
    seen, stack, cust = set(), [MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)], None
    while stack:
        e = stack.pop()
        if e is None or e.get_path_name() in seen: continue
        seen.add(e.get_path_name())
        if e.get_class().get_name() == 'MaterialExpressionCustom': cust = e; break
        stack += list(MEL.get_inputs_for_material_expression(m, e))
    code = str(cust.get_editor_property('code'))
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\houses_custom_backup359.hlsl", "w").write(code)
    A_OLD = "float p2 = pk - oneTile * 100000.0;"
    A_NEW = "float p2 = floor(pk + 0.5) - oneTile * 100000.0;          // rounded: at ~100000 a float only resolves ~0.008"
    B_OLD = "if (hid > 0.5)\n{"
    B_NEW = """// ---- half windows next to a hidden tile ----
// The green window is split across the seam of a tile pair (columns 0|1, 2|3, ...); in image space its half always sits
// at the tile's x = 1 edge (column 2 of a pair is mirrored). If the partner tile is hidden, this tile would keep half a
// window: draw the empty image over a strip of GreenStripWidth (0..1 of a tile) along that edge.
float hidP = 0.0;
if (HideWindows > 0.5 && isWall > 0.5 && GreenStripWidth > 0.0 && hid < 0.5)
{
    float pcol = fl + ((parity < 0.5) ? 1.0 : -1.0);              // the partner column
    if (pcol > -0.5 && pcol < wn - 0.5)
    {
        float cenP = (pcol + 0.5) / wn;
        float slotP = clamp(floor(cenP * 18.0 - 0.02), 0.0, 17.0);
        float chP = floor(slotP / 6.0);
        float s6P = slotP - chP * 6.0;
        float cvP = chP < 0.5 ? c0 : (chP < 1.5 ? c1 : c2);
        float covP = fmod(floor((cvP + 0.5) / exp2(3.0 * s6P)), 8.0);
        hidP = (floor(v) < covP - 0.5) ? 1.0 : 0.0;
    }
}
if (hidP > 0.5 && (slotI < 0.5 || (slotI > 1.5 && slotI < 3.5)) && uvm.x > 1.0 - GreenStripWidth)
{
    qS = qm; dxS = dxm; dyS = dym;
    slotI = (ground > 0.5) ? 1.0 : ((oneTile > 0.5) ? 5.0 : 4.0);   // the empty version of this tile, only in the strip
}
if (hid > 0.5)
{"""
    for o in (A_OLD, B_OLD):
        if code.count(o) != 1: raise Exception("expected exactly one match for: %r (found %d)" % (o, code.count(o)))
    code = code.replace(A_OLD, A_NEW).replace(B_OLD, B_NEW)
    # new input + parameter
    ins = list(cust.get_editor_property('inputs'))
    names = [str(i.get_editor_property('input_name')) for i in ins]
    if 'GreenStripWidth' not in names:
        ci = unreal.CustomInput()
        ci.set_editor_property('input_name', 'GreenStripWidth')
        ins.append(ci)
        cust.set_editor_property('inputs', ins)
    cust.set_editor_property('code', code)
    pos = (cust.get_editor_property('material_expression_editor_x') - 400, cust.get_editor_property('material_expression_editor_y') + 900)
    p = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, pos[0], pos[1])
    p.set_editor_property('parameter_name', 'GreenStripWidth')
    p.set_editor_property('default_value', 0.3)
    ok = MEL.connect_material_expressions(p, '', cust, 'GreenStripWidth')
    out.append("connected GreenStripWidth: %s" % ok)
    MEL.recompile_material(m)
    out.append("custom inputs now: %s" % [str(i.get_editor_property('input_name')) for i in cust.get_editor_property('inputs')])
    out.append("rounding line in: %s; strip block in: %s" % (A_NEW in str(cust.get_editor_property('code')), 'hidP' in str(cust.get_editor_property('code'))))
    out.append("recompiled (not saved)")
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
