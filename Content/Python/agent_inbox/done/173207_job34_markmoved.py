# The move was done in memory but never flagged as a change, so Save All skipped it (and Play loads
# actors from disk). Flag every moved sewer actor as changed so Save All writes it.
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mine = [a for a in eas.get_all_level_actors() if a.get_class().get_name() == "BP_SewerNode_C" or
        a.get_actor_label().startswith("SewerNetwork_GENERATED")]
for a in mine:
    a.modify()
    root = a.get_editor_property("root_component")
    if root:
        root.modify()
U = unreal.EditorLoadingAndSavingUtils
print("flagged %d actors; unsaved packages now: %d" % (len(mine), len(list(U.get_dirty_map_packages()))))
s = [a for a in mine if a.get_actor_label() == "SL_023_Shaft"][0]
print("SL_023_Shaft at", s.get_actor_location())
