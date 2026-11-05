"""SewerDefinitive with v2 water: py sewer_def.py
Builds the level SewerDefinitive from import/sewerdef_layout.json (SewerDefinitive.fbx)."""
import unreal, traceback, importlib, os, time
out = os.path.join(unreal.Paths.project_content_dir(), "Python", "scan_out.txt")
open(out, "w").write("def started\n")
try:
    import sewer_setup, sewer_builder, sewer_boxcol, sewer_simplecol, sewer_layout_trial
    for m in (sewer_setup, sewer_simplecol, sewer_boxcol, sewer_builder, sewer_layout_trial):
        importlib.reload(m)
    open(out, "a").write("material: %s\n" % sewer_setup.make_flow_material(v2=True))
    sewer_builder.HUB_FLOW_VERSION = 2
    sewer_builder.GENERATED_FOLDER = "/Game/Sewers/Generated/SewerDefinitive"   # own meshes: no clash with other levels
    sewer_builder.WATER_MATERIAL = "/Game/Sewers/Materials/MI_SewerWaterV2_Opaque"
    t = time.time()
    sewer_layout_trial.run(name="sewerdef_layout.json", level="/Game/Sewers/Maps/Sewers")
    try:
        sewer_layout_trial.add_lights()
    except Exception:
        open(out, "a").write("lights: " + traceback.format_exc())
    sewer_simplecol._refresh_level()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    open(out, "a").write("built in %.0f s, hub solve iterations %s\n" % (time.time() - t, sewer_builder._HUB_V2_ITERS))
except Exception:
    open(out, "a").write(traceback.format_exc())
