import unreal, collections
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
def lvl(a):
    try:
        return a.get_level().get_outermost().get_name()
    except Exception as e:
        return "?%s" % e
dyn = [a for a in acts if a.get_class().get_name() == "DynamicMeshActor"]
print("dynamic mesh actors:", len(dyn))
print("their levels:", collections.Counter(lvl(a) for a in dyn))
print("labels:", [a.get_actor_label() for a in dyn[:10]])
print("folders:", collections.Counter(str(a.get_folder_path()) for a in dyn).most_common(5))
nodes = [a for a in acts if a.get_class().get_name() == "BP_SewerNode_C"]
print("node levels:", collections.Counter(lvl(a) for a in nodes))
net = [a for a in acts if a.get_actor_label() == "SewerNetwork_GENERATED"]
print("network level:", [lvl(a) for a in net])
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("streaming:", [(str(s.get_editor_property("world_asset").get_asset_name()) if hasattr(s, "get_editor_property") else s) for s in unreal.EditorLevelUtils.get_levels(w)][:20] if hasattr(unreal.EditorLevelUtils, "get_levels") else "n/a")
print("all levels:", [l.get_outermost().get_name() for l in unreal.EditorLevelUtils.get_levels(w)])
if dyn:
    d = dyn[0]
    print("first dyn at", d.get_actor_location(), "comp:", [c.get_name() for c in d.get_components_by_class(unreal.DynamicMeshComponent)])
