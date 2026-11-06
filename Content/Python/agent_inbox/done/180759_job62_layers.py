import unreal
out = []
P = "/Game/Levels/DataLayers"
NAMES = ["DL_TheWhisperingBell","DL_TrollskullAlley","DL_Mountain","DL_Sea","DL_Sewers","DL_Sky","DL_Streets","DL_Walls","DL_WalkingStatues","DL_ReferenceMap"]
at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
def layers(a):
    try: return [x for x in a.get_editor_property('data_layer_assets') if x]
    except Exception: return []
# collect members before renaming (by asset object, survives rename)
sew_asset = unreal.load_asset(P + "/DL_Sewers"); sky_asset = unreal.load_asset(P + "/DL_Sky")
sewers = [a for a in acts if sew_asset in layers(a)]
sky = [a for a in acts if sky_asset in layers(a)]
out.append("members sewers=%d sky=%d" % (len(sewers), len(sky)))
# 1. rename editor layers to EDL_
data = []
for n in NAMES:
    a = unreal.load_asset(P + "/" + n)
    if a is None: out.append("missing " + n); continue
    data.append(unreal.AssetRenameData(a, P, "EDL_" + n[3:]))
ok = at.rename_assets(data)
out.append("rename ok=%s" % ok)
for n in NAMES:
    out.append("  %s exists=%s  EDL exists=%s" % (n, eal.does_asset_exist(P + "/" + n), eal.does_asset_exist(P + "/EDL_" + n[3:])))
# 2. runtime layers
sub = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
made = {}
for n, col in (("RDL_Sewers", unreal.Color(40, 120, 255, 255)), ("RDL_Sky", unreal.Color(255, 200, 40, 255))):
    path = P + "/" + n
    asset = unreal.load_asset(path) if eal.does_asset_exist(path) else at.create_asset(n, P, unreal.DataLayerAsset, unreal.DataLayerFactory())
    asset.set_editor_property("data_layer_type", unreal.DataLayerType.RUNTIME)
    try: asset.set_editor_property("debug_color", col)
    except Exception: pass
    inst = None
    for d in sub.get_all_data_layers():
        try:
            if d.get_asset() == asset: inst = d
        except Exception: pass
    if inst is None:
        prm = unreal.DataLayerCreationParameters()
        prm.set_editor_property("data_layer_asset", asset)
        inst = sub.create_data_layer_instance(prm)
    sub.set_data_layer_initial_runtime_state(inst, unreal.DataLayerRuntimeState.ACTIVATED)
    made[n] = inst
    out.append("%s instance=%s runtime=%s initial=%s clientonly=%s" % (n, inst.get_name() if inst else None, inst.is_runtime(), inst.get_initial_runtime_state(), inst.is_client_only()))
# 3. membership + tags + always loaded
for n, group in (("RDL_Sewers", sewers), ("RDL_Sky", sky)):
    tag = unreal.Name(n)
    for a in group:
        a.modify()
        t = list(a.tags)
        if tag not in t: t.append(tag); a.tags = t
        if a.get_editor_property("is_spatially_loaded"): a.set_editor_property("is_spatially_loaded", False)
    r = sub.add_actors_to_data_layer(group, made[n])
    out.append("%s added=%s n=%d" % (n, r, len(group)))
    chk = sum(1 for a in group if made[n].get_asset() in layers(a))
    out.append("   verified in layer: %d, tagged: %d, spatial: %d" % (chk, sum(1 for a in group if tag in a.tags), sum(1 for a in group if a.get_editor_property("is_spatially_loaded"))))
out.append("dirty map pkgs: %d  content: %d" % (len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()), len(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())))
print("\n".join(out))
