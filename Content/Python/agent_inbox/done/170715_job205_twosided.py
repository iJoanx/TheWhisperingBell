import unreal
out = []
for p in ('/Game/Sewers/Materials/MI_SewerWaterV2_Opaque', '/Game/Level/Streets/Materials/M_Master_Water_Inst'):
    mi = unreal.load_asset(p)
    o = mi.get_editor_property('base_property_overrides')
    o.set_editor_property('override_two_sided', True)
    o.set_editor_property('two_sided', True)
    mi.set_editor_property('base_property_overrides', o)
    unreal.MaterialEditingLibrary.update_material_instance(mi)
    o2 = mi.get_editor_property('base_property_overrides')
    out.append("%s override_two_sided=%s two_sided=%s" % (p, o2.get_editor_property('override_two_sided'), o2.get_editor_property('two_sided')))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump205.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
