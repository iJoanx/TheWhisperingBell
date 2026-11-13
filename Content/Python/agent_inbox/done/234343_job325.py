import unreal, importlib, sys, time
out = []
def done():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump325.txt", "w", encoding="utf-8").write("\n".join(out))
try:
    import walls_spline as ws
    BEL = unreal.BlueprintEditorLibrary
    bp = unreal.EditorAssetLibrary.load_asset(ws.BP_PATH)
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        cdo.get_editor_property("DoorRotations"); out.append("variable already there")
    except Exception:
        BEL.add_member_variable(bp, "DoorRotations", BEL.get_array_type(ws._struct_type(BEL, unreal.Rotator)))
        BEL.set_blueprint_variable_instance_editable(bp, "DoorRotations", True)
        BEL.compile_blueprint(bp)
        out.append("added DoorRotations (not saved)")
    t0 = time.time()
    ws = importlib.reload(sys.modules["walls_spline"])
    ws.start()
    out.append("reloaded + watcher restarted")
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    walls = [a for a in eas.get_all_level_actors() if ws._is_wall(a)]
    for a in walls:
        n = len([c for c in a.get_components_by_class(unreal.DynamicMeshComponent) if c.get_name().startswith(ws.DOOR_COMP_PREFIX)])
        out.append("%s: doors=%d DoorRotations=%s" % (a.get_actor_label(), n, len(a.get_editor_property("DoorRotations") or [])))
except Exception as e:
    import traceback; out.append("ERR " + traceback.format_exc()[-1500:])
done(); print("ok")
