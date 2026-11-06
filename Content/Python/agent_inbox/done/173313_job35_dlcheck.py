import unreal, collections
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
asset = unreal.load_asset("/Game/Levels/DataLayers/DL_Sewers")
mine = [a for a in eas.get_all_level_actors() if a.get_class().get_name() == "BP_SewerNode_C" or
        a.get_actor_label().startswith("SewerNetwork_GENERATED")]
def dls(a):
    try:
        return tuple(sorted(str(x.get_name()) for x in a.get_editor_property("data_layer_assets") if x))
    except Exception as e:
        return ("?",)
print("sewer actors:", len(mine))
print("their data layers:", collections.Counter(dls(a) for a in mine))
