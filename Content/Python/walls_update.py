"""Brings the wall kit up to date after exporting from Wall.blend (wall_export in Blender):
re-imports every piece with its collision, makes the door picture + material, adds the
DoorsOutside setting to BP_WallSpline, rebuilds every wall in the open level (towers, doors)
and saves. Open the level with the walls first.
    py walls_update.py              -> log in Content/Python/walls_update_out.txt"""
import os
import importlib
import traceback
import unreal

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "walls_update_out.txt")


def log(msg):
    open(out, "a").write(msg + "\n")
    unreal.log("WALLS " + msg)


open(out, "w").write("walls update started\n")
try:
    import walls_spline
    import walls_setup
    importlib.reload(walls_spline)
    importlib.reload(walls_setup)
    walls_spline.stop()
    walls_spline.make_door_assets()
    log("door picture + material made")
    for line in walls_setup.reimport_all():
        log(line)
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if walls_spline._is_wall(a):
            log("%s: %d doors" % (a.get_actor_label(), len(a.get_editor_property("DoorBoxes") or [])))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    walls_spline.start()
    log("done")
except Exception:
    log(traceback.format_exc())
