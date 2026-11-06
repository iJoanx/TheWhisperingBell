# After the bake: collision, DL_Sewers data layer, outliner folders, and a check. Saves nothing.
import unreal, collections, sys
sb = sys.modules["sewer_builder"]
import sewer_boxcol, sewer_simplecol
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
nodes = [a for a in acts if sb._is_node(a)]
nets = [a for a in acts if a.get_actor_label().startswith(sb.NETWORK_LABEL)]
print("nodes:", len(nodes), " network actors:", len(nets))

sewer_boxcol.apply_level(save=False)
sewer_simplecol._refresh_level()
print("collision applied")

dls = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
asset = unreal.load_asset("/Game/Levels/DataLayers/DL_Sewers")
inst = None
for name in ("get_data_layer_instance_from_asset", "get_data_layer_instance"):
    f = getattr(dls, name, None)
    if f and inst is None:
        try:
            inst = f(asset)
        except Exception as e:
            print(name, "failed:", e)
if inst is None:
    for d in dls.get_all_data_layers():
        try:
            if d.get_asset() == asset:
                inst = d
        except Exception:
            pass
print("DL_Sewers instance:", inst)
mine = nodes + nets
ok = False
if inst is not None:
    try:
        ok = dls.add_actors_to_data_layer(mine, inst)
    except Exception as e:
        print("add_actors_to_data_layer:", e)
if not ok:
    for a in mine:
        a.set_editor_property("data_layer_assets", [asset])
def in_dl(a):
    try:
        return asset in list(a.get_editor_property("data_layer_assets"))
    except Exception:
        return None
print("in DL_Sewers:", collections.Counter(in_dl(a) for a in mine))

comps = inst_count = 0
for a in nets:
    hs = a.get_components_by_class(unreal.InstancedStaticMeshComponent)
    comps += len(hs)
    inst_count += sum(c.get_instance_count() for c in hs)
print("network components:", comps, "instances:", inst_count)
nomesh = nocol = 0
for n in nodes:
    if sb._is_end(sb._node_type(n)):
        continue
    c = n.get_component_by_class(unreal.StaticMeshComponent)
    sm = c.get_editor_property("static_mesh") if c else None
    if not sm:
        nomesh += 1
        continue
    if not len(sm.get_editor_property("body_setup").get_editor_property("agg_geom").get_editor_property("convex_elems")):
        nocol += 1
print("built nodes without mesh:", nomesh, " without collision:", nocol)
print("old SL_ / network actors from before left over:",
      len([a for a in acts if a.get_actor_label() == sb.NETWORK_LABEL]))
