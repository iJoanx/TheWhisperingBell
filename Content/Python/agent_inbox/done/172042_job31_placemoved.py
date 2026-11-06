# Fast redo after a lost save: put the SewersFinal nodes back and rebuild only the network, reusing
# the node meshes (with their collision) that the last build already saved. No undo transaction.
# Then let go of every Unreal object Python holds, so nothing from these scripts is in the way of the save.
import unreal, importlib, time, sys, gc
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not w.get_path_name().startswith("/Game/Levels/PersistentLevel_WP."):
    raise RuntimeError("PersistentLevel_WP is not the open level")
import sewer_builder as sb, sewer_layout_trial as lt, sewer_simplecol
for m in (sb, lt, sewer_simplecol):
    importlib.reload(m)
sb.HUB_FLOW_VERSION = 2
sb.GENERATED_FOLDER = "/Game/Sewers/Generated/SewersFinal"
sb.WATER_MATERIAL = "/Game/Sewers/Materials/MI_SewerWaterV2_Opaque"
sb.NETWORK_SPLIT = True
sb.NETWORK_CELL = 12800.0
EAL = unreal.EditorAssetLibrary
t = time.time()
actors = lt.spawn(lt.load("sewersfinal_layout.json"))
missing = []
for a in actors.values():
    a.set_folder_path("Sewers/" + str(a.get_editor_property("NodeType")))
    comp = a.get_component_by_class(unreal.StaticMeshComponent)
    if sb._is_end(sb._node_type(a)):
        comp.set_static_mesh(None)
        continue
    path = "%s/SM_SewerNode_%s" % (sb.GENERATED_FOLDER, sb._safe(a.get_actor_label()))
    sm = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if sm is None:
        missing.append(a.get_actor_label())
        continue
    comp.set_static_mesh(sm)
print("nodes placed: %d, node meshes missing: %d %s" % (len(actors), len(missing), missing[:10]))
sb.use_definitive()
nodes = [a for a in sb._actors() if sb._is_node(a)]
warnings = []
edges, per_node = sb._gather(nodes, warnings)
segs = sb._rebuild_network(edges, nodes, per_node)
print("network: %d actors, %d passage segments, %.0f s" % (len(sb.network_actors()), segs, time.time() - t))
sewer_simplecol._refresh_level()

asset = unreal.load_asset("/Game/Levels/DataLayers/DL_Sewers")
dls = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
inst = None
for d in dls.get_all_data_layers():
    try:
        if d.get_asset() == asset:
            inst = d
    except Exception:
        pass
mine = nodes + sb.network_actors()
print("added to DL_Sewers:", dls.add_actors_to_data_layer(mine, inst) if inst else "no DL_Sewers instance")

# drop every Unreal object our scripts keep in memory
del actors, nodes, mine, edges, per_node
for name, module in list(sys.modules.items()):
    if module is None or not name.startswith("sewer_"):
        continue
    for key, value in list(vars(module).items()):
        if key.startswith("__"):
            continue
        try:
            if isinstance(value, (dict, list, set)) and key.startswith("_") and key.upper() == key:
                value.clear()          # caches like _ORIENTED, _OUTER, _TRIS (not settings)
        except Exception:
            pass
for name in ("sewer_builder", "sewer_layout_trial", "sewer_simplecol", "sewer_boxcol", "sewer_setup"):
    sys.modules.pop(name, None)       # the next import starts clean
gc.collect()
print("python caches cleared")
