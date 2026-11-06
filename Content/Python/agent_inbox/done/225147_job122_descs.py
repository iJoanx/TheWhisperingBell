import unreal
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
loaded_names = set(a.get_name() for a in acts)
descs = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
print("descs:", len(descs))
print("sample:", descs[0].to_dict() if hasattr(descs[0], 'to_dict') else descs[0])
nl = []
for d in descs:
    dd = d.to_dict()
    path = str(dd.get('actor_path', dd.get('actor_name', '')))
    name = path.split('.')[-1]
    if name not in loaded_names: nl.append(dd)
print("not loaded:", len(nl))
for dd in nl: print("  ", {k: str(v)[:90] for k, v in dd.items() if k in ('label', 'native_class', 'actor_path', 'bounds', 'is_spatially_loaded', 'data_layer_instance_names', 'actor_package')})
