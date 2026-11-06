import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("world:", w.get_path_name() if w else None)
print("unsaved:", len(list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())))
