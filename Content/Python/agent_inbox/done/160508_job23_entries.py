import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    n = a.get_class().get_name()
    if "Sewer_Entry" in n or "Sewer_Exit" in n:
        l = a.get_actor_location()
        print(n, a.get_actor_label(), round(l.x), round(l.y), round(l.z))
