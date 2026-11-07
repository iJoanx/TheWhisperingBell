import unreal
out = []
MEL = unreal.MaterialEditingLibrary
for p in ('/Game/Sewers/Materials/M_SewerWaterFlowV2', '/Game/Water/M_SewerWaterFlow_SLW'):
    m = unreal.load_asset(p)
    row = [p.split('/')[-1], str(m.get_editor_property('shading_model')).split('.')[-1]]
    for prop in ('MP_BASE_COLOR', 'MP_EMISSIVE_COLOR', 'MP_OPACITY', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_METALLIC', 'MP_SPECULAR'):
        n = MEL.get_material_property_input_node(m, getattr(unreal.MaterialProperty, prop))
        row.append("%s=%s" % (prop[3:], n.get_class().get_name().replace('MaterialExpression', '') if n else '-'))
    out.append("  ".join(row))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump211.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
