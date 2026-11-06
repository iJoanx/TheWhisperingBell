import unreal
L = unreal.WorldPartitionBlueprintLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
d = [x.to_dict() for x in L.get_actor_descs() if str(x.to_dict().get('label')) == 'Waterdeep']
print("pinned earlier")
wd = [a for a in eas.get_all_level_actors() if a.get_actor_label() == 'Waterdeep']
print("loaded now:", len(wd))
for a in wd:
    o, e = a.get_actor_bounds(False)
    if abs((o - e).x - d[0]['bounds'].min.x) < 1.0:
        a.modify(); a.root_component.modify()
        a.set_actor_location(a.get_actor_location() + unreal.Vector(-1800, -500, 0), False, True)
        o2, e2 = a.get_actor_bounds(False)
        print("moved Waterdeep; bounds min", o - e, "->", o2 - e2)
    else:
        print("Waterdeep already moved")
print("total actors:", len(eas.get_all_level_actors()), "dirty:", len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()))
