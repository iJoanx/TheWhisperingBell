import unreal, collections, json, os, math
PY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ue = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ue.get_editor_world()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
dls = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
acts = eas.get_all_level_actors()
def dl_names(a):
    try:
        return tuple(sorted(str(d.get_data_layer_short_name()) for d in dls.get_data_layer_instances_for_actor(a)))  # noqa
    except Exception:
        try:
            return tuple(sorted(str(x) for x in a.get_editor_property("data_layer_assets")))
        except Exception as e:
            return ("?%s" % e,)
nodes = [a for a in acts if a.get_class().get_name() == "BP_SewerNode_C"]
print("node data layers:", collections.Counter(dl_names(a) for a in nodes))
print("node labels:", sorted(a.get_actor_label() for a in nodes)[:5])
print("node folders:", collections.Counter(str(a.get_folder_path()) for a in nodes).most_common(3))
# compare positions to the old layout (are these the old sewers?)
old = json.load(open(os.path.join(PY, "import", "sewerdef_layout.json")))
new = json.load(open(os.path.join(PY, "import", "sewersfinal_layout.json")))
def near(lay):
    pts = [(n["x"], n["y"], n["z"]) for n in lay["nodes"]]
    hits = 0
    for a in nodes:
        l = a.get_actor_location()
        if min(math.dist((l.x, l.y, l.z), p) for p in pts) < 10:
            hits += 1
    return hits
print("nodes matching OLD layout:", near(old), " matching NEW layout:", near(new))
smas = [a for a in acts if a.get_class().get_name() == "StaticMeshActor"]
sew = [a for a in smas if "Sewer" in a.get_actor_label() or "SL_" in a.get_actor_label()]
print("sewer-ish static mesh actors:", [(a.get_actor_label(), dl_names(a), len(a.get_components_by_class(unreal.InstancedStaticMeshComponent))) for a in sew][:20])
print("data layers of static mesh actors:", collections.Counter(dl_names(a) for a in smas).most_common(12))
other = collections.Counter((a.get_class().get_name(), dl_names(a)) for a in acts if "Sewer" in a.get_class().get_name() or any("Sewer" in d for d in dl_names(a)))
print("everything in / about sewers:", other.most_common(20))
n0 = nodes[0]
c = n0.get_component_by_class(unreal.StaticMeshComponent)
print("node 0 mesh:", n0.get_actor_label(), c.get_editor_property("static_mesh").get_path_name() if c and c.get_editor_property("static_mesh") else None)
try:
    print("node 0 spatially loaded:", n0.get_editor_property("is_spatially_loaded") if hasattr(n0, "get_editor_property") else "?")
except Exception as e:
    print("spatial:", e)
ws = w.get_world_settings()
wpo = ws.get_editor_property("world_partition")
for p in ("editor_hash", "runtime_hash", "b_enable_streaming", "enable_streaming"):
    try:
        print(p, wpo.get_editor_property(p))
    except Exception as e:
        print(p, "-")
