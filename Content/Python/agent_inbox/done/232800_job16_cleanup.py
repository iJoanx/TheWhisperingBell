import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tmp = [a for a in eas.get_all_level_actors() if a.get_actor_label().startswith("BirdsEye_TEMP_")]
print("leftover picture copies:", len(tmp))
pkg = tmp[0].get_level().get_outermost() if tmp else None
dirty_before = [str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
print("unsaved maps before:", dirty_before)
with unreal.ScopedEditorTransaction("Remove bird's-eye picture copies"):
    for a in tmp:
        eas.destroy_actor(a)
left = [a for a in eas.get_all_level_actors() if a.get_actor_label().startswith("BirdsEye_TEMP_")]
print("left:", len(left))
if pkg is not None and pkg.get_name() not in dirty_before:
    ok = unreal.EditorLoadingAndSavingUtils.save_packages([pkg], True)
    print("saved", pkg.get_name(), ok)
else:
    print("not saved: that level already had other unsaved changes:", pkg.get_name() if pkg else None)
