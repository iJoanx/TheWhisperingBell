import unreal
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump361.txt", "w").write("\n".join(out))
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
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\houses_custom_backup361.hlsl", "w").write(code)
    A_OLD = "&& floor(saturate(qm.x) * 64.0) >= 64.0 - floor(GreenStripWidth * 64.0 + 0.5))"
    A_NEW = "&& (ground > 0.5 || floor(saturate(qm.x) * 64.0) >= 64.0 - floor(GreenStripWidth * 64.0 + 0.5)))   // ground floor: the whole tile (pairs)"
    B_OLD = A_OLD
    B_NEW = A_NEW
    for o in (A_OLD,):
        if code.count(o) != 1: raise Exception("expected one match for %r, found %d" % (o, code.count(o)))
    code = code.replace(A_OLD, A_NEW)
    cust.set_editor_property('code', code)
    MEL.recompile_material(m)
    c2 = str(cust.get_editor_property('code'))
    out.append("ground rule in: %s" % (A_NEW in c2))
    out.append("recompiled (not saved)")
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
