import unreal, collections, json, os
ue = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ue.get_editor_world()
print("world:", w.get_path_name())
wp = None
try:
    wp = w.get_world_partition() if hasattr(w, "get_world_partition") else None
except Exception as e:
    print("wp err", e)
print("world partition:", wp)
ws = w.get_world_settings()
for p in ("world_partition", "enable_world_bounds_checks"):
    try:
        print(p, ws.get_editor_property(p))
    except Exception as e:
        pass
try:
    rg = ws.get_editor_property("world_partition").get_editor_property("runtime_hash")
    print("runtime hash:", rg)
    for p in ("runtime_grids", "grids"):
        try:
            for g in rg.get_editor_property(p):
                print("  grid", g.get_editor_property("grid_name"), "cell", g.get_editor_property("cell_size"), "range", g.get_editor_property("loading_range"))
        except Exception as e:
            print("  ", p, e)
except Exception as e:
    print("grid info:", e)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
print("loaded actors:", len(acts))
cls = collections.Counter(a.get_class().get_name() for a in acts)
print("classes:", cls.most_common(25))
print("sewer nodes:", cls.get("BP_SewerNode_C", 0))
dls = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
try:
    for inst in dls.get_all_data_layers():
        try:
            print("data layer:", inst.get_data_layer_short_name() if hasattr(inst, "get_data_layer_short_name") else inst.get_name(), inst.get_class().get_name())
        except Exception as e:
            print("data layer", inst, e)
except Exception as e:
    print("data layers:", e)
land = [a for a in acts if "Landscape" in a.get_class().get_name()]
print("landscapes:", [(a.get_actor_label(), a.get_class().get_name()) for a in land][:10])
# ground height above a few nodes of the new layout
lay = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "import", "sewersfinal_layout.json")))
import random
random.seed(1)
probe = random.sample(lay["nodes"], 25)
above = []
for n in probe:
    s = unreal.Vector(n["x"], n["y"], 200000.0)
    e = unreal.Vector(n["x"], n["y"], -200000.0)
    hit = unreal.SystemLibrary.line_trace_single(w, s, e, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    if hit:
        h = hit.to_tuple()
        above.append((n["id"], n["type"], round(n["z"]), round(h[4].z) if h[4] else None, str(h[9].get_actor_label()) if h[9] else None))
    else:
        above.append((n["id"], n["type"], round(n["z"]), None, None))
for a in above:
    print("node", a)
b = unreal.EditorLevelLibrary.get_editor_world()
