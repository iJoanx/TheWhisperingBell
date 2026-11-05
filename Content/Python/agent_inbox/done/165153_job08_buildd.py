import unreal, importlib, time
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
print("open level:", w)
if not w.startswith("/Game/Sewers/Maps/Sewers."):
    dirty = [str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError("not switching levels: unsaved maps %s" % dirty)
    print("load:", les.load_level("/Game/Sewers/Maps/Sewers"))
import sewer_setup, sewer_simplecol, sewer_boxcol, sewer_builder as sb
for m in (sewer_setup, sewer_simplecol, sewer_boxcol, sb):
    importlib.reload(m)
sb.HUB_FLOW_VERSION = 2
sb.GENERATED_FOLDER = "/Game/Sewers/Generated/SewerDefinitive"
sb.WATER_MATERIAL = "/Game/Sewers/Materials/MI_SewerWaterV2_Opaque"
print("nodes:", len([a for a in sb._actors() if sb._is_node(a)]))
class _NoDialog:
    @staticmethod
    def show_message(*a, **k):
        print("DIALOG:", a[1] if len(a) > 1 else a)
        return unreal.AppReturnType.OK
class _U:
    def __getattr__(self, n):
        return _NoDialog if n == "EditorDialog" else getattr(unreal, n)
t = time.time()
sb.unreal = _U()
try:
    sb.build()
finally:
    sb.unreal = unreal
print("built in %.0f s" % (time.time() - t))
les.save_current_level()
import os
print(open(os.path.join(os.path.dirname(sb.__file__), "build_report.txt")).read()[:3000])
