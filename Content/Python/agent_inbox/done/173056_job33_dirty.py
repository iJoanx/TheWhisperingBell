import unreal
U = unreal.EditorLoadingAndSavingUtils
maps = [str(p.get_name()) for p in U.get_dirty_map_packages()]
print("unsaved level/actor packages:", len(maps))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
s = [a for a in eas.get_all_level_actors() if a.get_actor_label() == "SL_023_Shaft"]
print("SL_023_Shaft in editor:", s[0].get_actor_location() if s else None)
pkg = s[0].get_package().get_name() if s and hasattr(s[0], "get_package") else s[0].get_outermost().get_name()
print("its package:", pkg, "unsaved" if pkg in maps else "saved")
