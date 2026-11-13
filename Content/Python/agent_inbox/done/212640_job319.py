import traceback, unreal
out = []
try:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    pairs = [a for a in eas.get_all_level_actors() if a.get_class().get_name() == "BP_DoorPair_C"]
    out.append("pairs in level: %d" % len(pairs))
    if pairs:
        a = pairs[0]
        cls = a.get_class()
        out.append("class %s" % cls.get_path_name())
        for c in a.get_components_by_class(unreal.SceneComponent):
            p = c.get_attach_parent()
            out.append("  comp %s (%s) parent %s rel %s %s" % (c.get_name(), c.get_class().get_name(), p.get_name() if p else None,
                       c.get_editor_property("relative_location"), c.get_editor_property("relative_rotation")))
        bp = unreal.load_asset(cls.get_path_name().rsplit(".", 1)[0])
        out.append("bp asset %s" % (bp.get_path_name() if bp else None))
    out.append("BlueprintEditorLibrary funcs: %s" % [f for f in dir(unreal.BlueprintEditorLibrary) if not f.startswith("_")])
    import walls_spline as ws
    out.append("DOOR_W %s DOOR_H %s" % (ws.DOOR_W, ws.DOOR_H))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump319.txt", "w").write("\n".join(out))
