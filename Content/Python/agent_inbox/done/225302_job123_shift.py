import unreal, sys
OFF = unreal.Vector(-1800.0, -500.0, 0.0)
SKIP = ('WorldDataLayers', 'WorldPartitionMiniMap', 'WorldSettings', 'ChaosDebugDrawActor')
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
L = unreal.WorldPartitionBlueprintLibrary
# load the unloaded Waterdeep reference mesh so it moves too
descs = L.get_actor_descs()
want = [d for d in descs if str(d.to_dict().get('label')) == 'Waterdeep']
if want:
    try:
        L.load_actors([d.to_dict()['guid'] for d in want]); print("loaded Waterdeep")
    except Exception as e: print("load Waterdeep failed:", e)
acts = eas.get_all_level_actors()
ref_a = [a for a in acts if a.get_actor_label() == 'BP_WB_SW14']; ref_b = [a for a in acts if a.get_actor_label() == 'SL_023_Shaft']
before_rel = (ref_b[0].get_actor_location() - ref_a[0].get_actor_location()) if ref_a and ref_b else None
moved = skipped = 0
for a in acts:
    cn = a.get_class().get_name()
    if any(s in cn for s in SKIP) or a.get_attach_parent_actor() is not None or a.root_component is None:
        skipped += 1; continue
    a.modify(); a.root_component.modify()
    a.set_actor_location(a.get_actor_location() + OFF, False, True)
    moved += 1
print("moved", moved, "skipped", skipped)
if before_rel:
    after_rel = ref_b[0].get_actor_location() - ref_a[0].get_actor_location()
    print("SW14 -> SL_023 offset before", before_rel, "after", after_rel)
# tell the wall / door watchers this is not an edit
for modname, fn, pred in (('walls_spline', '_signature', '_is_wall'), ('door_wrap', '_signature', '_is_pair')):
    m = sys.modules.get(modname)
    if not m: print(modname, "not loaded"); continue
    n = 0
    for a in eas.get_all_level_actors():
        if getattr(m, pred)(a):
            try: m._STATE["sig"][a.get_path_name()] = getattr(m, fn)(a); n += 1
            except Exception as e: print(modname, "sig err", e)
    print(modname, "signatures refreshed:", n)
# kill plane off
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
ws = w.get_world_settings(); ws.modify()
ws.set_editor_property('enable_world_bounds_checks', False)
print("world bounds checks (kill Z):", ws.get_editor_property('enable_world_bounds_checks'))
print("dirty map packages:", len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()))
