import unreal
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
sh = [a for a in acts if a.get_actor_label().startswith('SL_') and 'Shaft' in a.get_actor_label()]
print("shafts", len(sh))
for a in acts:
    if a.get_class().get_name() == 'BP_WB_Sewer_Entry_C':
        p = a.get_actor_location()
        ds = sorted(sh, key=lambda s: ((s.get_actor_location().x - p.x)**2 + (s.get_actor_location().y - p.y)**2))
        print(a.get_actor_label(), [ "%s %.0fm" % (s.get_actor_label(), (((s.get_actor_location().x - p.x)**2 + (s.get_actor_location().y - p.y)**2) ** 0.5) / 100) for s in ds[:3]])
