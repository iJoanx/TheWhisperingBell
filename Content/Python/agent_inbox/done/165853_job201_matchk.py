import unreal, collections
out = []
for name in ("M_PP_Underwater_Sea", "M_PP_Underwater_Sewage"):
    m = unreal.load_asset("/Game/Water/" + name)
    pref = m.get_path_name() + ":"
    kinds = collections.Counter(o.get_class().get_name() for o in unreal.ObjectIterator(unreal.MaterialExpression) if o.get_path_name().startswith(pref))
    out.append("%s num=%d kinds=%s" % (name, unreal.MaterialEditingLibrary.get_num_material_expressions(m), dict(kinds)))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump201.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
