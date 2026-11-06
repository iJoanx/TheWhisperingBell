import unreal, toolset_registry, inspect
print("toolset_registry:", [n for n in dir(toolset_registry) if not n.startswith("__")])
try:
    from toolset_registry import tool_call_impl
    print("tool_call_impl:", [n for n in dir(tool_call_impl) if not n.startswith("__")])
except Exception as e: print(e)
import editor_toolset.toolsets.blueprint as B
print("bp mod:", [n for n in dir(B) if not n.startswith("_")][:80])
da = unreal.load_asset("/Game/Levels/DataLayers/DL_Sewers")
print("DLA props:", [p for p in dir(da) if not p.startswith("_") and not callable(getattr(da,p,None))][:50])
for p in ("data_layer_type","debug_color","load_filter","b_supports_actor_filters"):
    try: print(" ", p, da.get_editor_property(p))
    except Exception as e: print(" ", p, "?")
s = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
d = s.get_all_data_layers()[0]
print("DLI attrs:", [p for p in dir(d) if "client" in p.lower() or "runtime" in p.lower() or "state" in p.lower() or "type" in p.lower()])
print("unreal names with ClientOnly:", [n for n in dir(unreal) if "DataLayer" in n])
# actors per data layer
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
from collections import Counter, defaultdict
c = Counter(); ex = defaultdict(list)
for a in acts:
    try: lays = s.get_data_layers_of_actor(a) if hasattr(s,"get_data_layers_of_actor") else a.get_data_layer_instances()
    except Exception as e: lays = []
    if not lays: c["<none>"] += 1; ex["<none>"].append(a.get_class().get_name())
    for l in lays:
        n = l.get_asset().get_name() if hasattr(l,"get_asset") and l.get_asset() else l.get_name()
        c[n] += 1
        if len(ex[n]) < 400: ex[n].append(a.get_class().get_name())
for k,v in c.items(): print("LAYER", k, v, Counter(ex[k]).most_common(8))
