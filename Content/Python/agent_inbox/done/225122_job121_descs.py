import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
loaded = set(a.get_path_name() for a in acts)
print("labels with kill:", [(a.get_actor_label(), a.get_class().get_name(), a.get_actor_location()) for a in acts if 'kill' in a.get_actor_label().lower() or 'Kill' in a.get_class().get_name()])
L = unreal.WorldPartitionBlueprintLibrary
print([n for n in dir(L) if not n.startswith('_')][:40])
try:
    ok, descs = L.get_actor_descs() if True else (None, None)
except Exception as e:
    descs = None; print("get_actor_descs err", e)
try:
    if descs is None:
        r = L.get_actor_descs(); print("raw", type(r))
except Exception as e: print("err2", e)
if descs:
    print("descs:", len(descs))
    un = [d for d in descs if str(d.get_editor_property('actor_path') if hasattr(d,'get_editor_property') else '') not in loaded]
    for d in descs:
        try:
            nm = d.get_editor_property('label'); cl = d.get_editor_property('native_class') if False else d.get_editor_property('class'); 
        except Exception: pass
    for d in descs[:3]: print("desc sample:", d)
    notloaded = []
    for d in descs:
        try:
            p = str(d.get_editor_property('actor_path'))
            if p.split('.')[-1] not in [x.split('.')[-1] for x in loaded]: notloaded.append((str(d.get_editor_property('label')), str(d.get_editor_property('native_class')), d.get_editor_property('bounds')))
        except Exception as e: notloaded.append(("err", str(e)[:80], None)); break
    print("not loaded:", notloaded[:20])
