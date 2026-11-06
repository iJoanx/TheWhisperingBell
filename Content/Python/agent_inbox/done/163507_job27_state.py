import unreal, json, os, math, collections
PY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("world:", w.get_path_name())
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
nodes = [a for a in acts if a.get_class().get_name() == "BP_SewerNode_C"]
nets = [a for a in acts if a.get_actor_label().startswith("SewerNetwork_GENERATED")]
new = json.load(open(os.path.join(PY, "import", "sewersfinal_layout.json")))["nodes"]
pts = [(n["x"], n["y"], n["z"]) for n in new]
def is_new(a):
    l = a.get_actor_location()
    return min(math.dist((l.x, l.y, l.z), p) for p in pts) < 10
print("nodes:", len(nodes), "at NEW layout positions:", sum(1 for a in nodes if is_new(a)))
print("network actors:", len(nets), [a.get_actor_label() for a in nets[:3]])
U = unreal.EditorLoadingAndSavingUtils
print("unsaved now:", len(list(U.get_dirty_map_packages())) + len(list(U.get_dirty_content_packages())))
