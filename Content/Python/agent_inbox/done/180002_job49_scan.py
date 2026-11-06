import unreal, json, asyncio, inspect
from collections import Counter, defaultdict
import toolset_registry._registry_interface as RI
def call(n, a, ts='editor_toolset.toolsets.blueprint.BlueprintTools'):
    r = RI.execute_tool(ts, n, a)
    if inspect.iscoroutine(r): r = asyncio.new_event_loop().run_until_complete(r)
    return r['returnValue'] if isinstance(r, dict) and 'returnValue' in r else r
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
def lays(a):
    try: return [x.get_name() for x in a.get_editor_property('data_layer_assets') if x]
    except Exception as e: return ["ERR"]
per = defaultdict(Counter)
for a in acts:
    L = lays(a) or ["<none>"]
    for l in L: per[l][a.get_class().get_name()] += 1
for l, c in per.items(): print("LAYER", l, sum(c.values()), c.most_common(10))
for a in acts:
    cn = a.get_class().get_name()
    if "Sewer_Entry" in cn or "Sewer_Exit" in cn:
        print("\nINST", a.get_actor_label(), cn, a.get_actor_location(), lays(a))
        for p in ("Level","Destination"):
            try: print("   ", p, a.get_editor_property(p))
            except Exception as e: print("   ", p, "?")
        for c in a.get_components_by_class(unreal.SceneComponent):
            extra = ""
            if isinstance(c, unreal.StaticMeshComponent): extra = str(c.static_mesh.get_name() if c.static_mesh else None) + " coll=" + str(c.get_collision_profile_name())
            if isinstance(c, unreal.ShapeComponent): extra = "coll=" + str(c.get_collision_profile_name())
            print("    COMP", c.get_name(), c.get_class().get_name(), c.get_world_location(), extra)
# IMC with key One
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for ad in ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/EnhancedInput","InputMappingContext")):
    if not str(ad.package_name).startswith("/Game"): continue
    imc = ad.get_asset()
    try:
        for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings"):
            k = m.get_editor_property("key").get_editor_property("key_name")
            if str(k) in ("One","NumPadOne"): print("IMC", ad.package_name, k, m.get_editor_property("action").get_path_name())
    except Exception as e:
        try:
            for m in imc.get_editor_property("mappings"):
                k = m.get_editor_property("key").get_editor_property("key_name")
                if str(k) in ("One","NumPadOne"): print("IMC", ad.package_name, k, m.get_editor_property("action").get_path_name())
        except Exception as e2: print("IMC err", ad.package_name, e2)
# blueprints with a key-1 event
f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine","Blueprint")], package_paths=["/Game/ThirdPerson","/Game/Level","/Game/Blueprints","/Game/Core","/Game/UI"], recursive_paths=True)
bps = ar.get_assets(f)
print("bps scanned", len(bps))
for ad in bps:
    p = str(ad.package_name) + "." + str(ad.asset_name)
    try:
        r = call('find_nodes', {'graph': {'refPath': p + ':EventGraph'}, 'title': 'One', 'entry_points_only': True})
        if r: print("KEY1?", p, r)
        r = call('find_nodes', {'graph': {'refPath': p + ':EventGraph'}, 'title': 'SwitchChar', 'entry_points_only': False})
        if r: print("SWITCHCHAR?", p, r)
        r = call('find_nodes', {'graph': {'refPath': p + ':EventGraph'}, 'title': 'Possess', 'entry_points_only': False})
        if r: print("POSSESS", p, len(r))
    except Exception as e: pass
