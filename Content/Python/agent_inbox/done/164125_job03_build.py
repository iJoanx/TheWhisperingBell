import unreal, importlib, time
dirty = [str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
print("unsaved maps:", dirty)
if dirty:
    raise SystemExit("not switching levels: the open map has unsaved changes")
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
print("load:", les.load_level("/Game/Sewers/Maps/Sewers"))
import sewer_setup, sewer_simplecol, sewer_boxcol, sewer_builder as sb
for m in (sewer_setup, sewer_simplecol, sewer_boxcol, sb):
    importlib.reload(m)
sb.HUB_FLOW_VERSION = 2
sb.GENERATED_FOLDER = "/Game/Sewers/Generated/SewerDefinitive"
sb.WATER_MATERIAL = "/Game/Sewers/Materials/MI_SewerWaterV2_Opaque"
print("nodes:", len([a for a in sb._actors() if sb._is_node(a)]))
_show = unreal.EditorDialog.show_message
unreal.EditorDialog.show_message = staticmethod(lambda *a, **k: unreal.AppReturnType.OK)
t = time.time()
try:
    sb.build()
finally:
    unreal.EditorDialog.show_message = _show
print("built in %.0f s" % (time.time() - t))
les.save_current_level()
import os
print(open(os.path.join(os.path.dirname(sb.__file__), "build_report.txt")).read()[:3000])
