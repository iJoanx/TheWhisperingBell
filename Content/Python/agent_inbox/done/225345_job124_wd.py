import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
wd = [a for a in eas.get_all_level_actors() if a.get_actor_label() == 'Waterdeep']
d = [x.to_dict() for x in unreal.WorldPartitionBlueprintLibrary.get_actor_descs() if str(x.to_dict().get('label')) == 'Waterdeep']
print("loaded:", len(wd), "desc bounds min:", d[0]['bounds'].min if d else None)
for a in wd:
    o, e = a.get_actor_bounds(False)
    print("current bounds min:", o - e, "location:", a.get_actor_location())
    # moved already if current min is 1800/500 lower than the saved descriptor
    if d and abs((o - e).x - d[0]['bounds'].min.x) < 1.0:
        a.modify(); a.root_component.modify()
        a.set_actor_location(a.get_actor_location() + unreal.Vector(-1800, -500, 0), False, True)
        print("moved Waterdeep ->", a.get_actor_location())
    else:
        print("Waterdeep already moved")
print("total actors:", len(eas.get_all_level_actors()))
