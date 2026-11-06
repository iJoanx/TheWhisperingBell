import unreal
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class().get_name() == 'BP_DayNightCycle_C':
        a.modify()
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            c.modify()
            c.set_collision_profile_name('NoCollision')
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            c.set_editor_property('generate_overlap_events', False)
            par = c.get_attach_parent()
            print("instance", c.get_name(), c.get_collision_profile_name(), c.get_collision_enabled(), "overlaps", c.get_editor_property('generate_overlap_events'), "parent", par.get_name() if par else None)
        print("package dirty-marked for", a.get_actor_label())
