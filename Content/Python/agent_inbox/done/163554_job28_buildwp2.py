# New sewer layout (SewersFinal.fbx) in PersistentLevel_WP: replace the SL_ nodes and the network, rebuild.
import unreal, importlib, time, json, os
PY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("world:", world.get_path_name())
if not world.get_path_name().startswith("/Game/Levels/PersistentLevel_WP."):
    raise RuntimeError("PersistentLevel_WP is not the open level")
dirty = sorted(set(str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()) |
               set(str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()))
json.dump(dirty, open(os.path.join(PY, "agent_inbox", "dirty_before_sewers.json"), "w"))
print("unsaved before the build:", len(dirty), dirty[:10])

import sewer_setup, sewer_simplecol, sewer_boxcol, sewer_builder as sb, sewer_layout_trial as lt
for m in (sewer_setup, sewer_simplecol, sewer_boxcol, sb, lt):
    importlib.reload(m)
sb.HUB_FLOW_VERSION = 2
sb.GENERATED_FOLDER = "/Game/Sewers/Generated/SewersFinal"
sb.WATER_MATERIAL = "/Game/Sewers/Materials/MI_SewerWaterV2_Opaque"
sb.NETWORK_SPLIT = True
sb.NETWORK_CELL = 12800.0

data = lt.load("sewersfinal_layout.json")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
old_net = [a for a in eas.get_all_level_actors() if a.get_actor_label().startswith(sb.NETWORK_LABEL)]
print("old network actors:", len(old_net))
t = time.time()
actors = lt.spawn(data)                      # removes the old SL_ nodes, spawns the new ones
print("spawned %d nodes in %.0f s" % (len(actors), time.time() - t))
for a in actors.values():
    a.set_folder_path("Sewers/" + str(a.get_editor_property("NodeType")))

# collision is applied by the next job (it has to come a few frames after the bake)
_later = sewer_boxcol.apply_level_later
sewer_boxcol.apply_level_later = lambda *a, **k: None


class _NoDialog:
    @staticmethod
    def show_message(*a, **k):
        print("DIALOG:", a[1] if len(a) > 1 else a)
        return unreal.AppReturnType.OK


class _U:
    def __dir__(self):
        return dir(unreal)

    def __getattr__(self, n):
        return _NoDialog if n == "EditorDialog" else getattr(unreal, n)


t = time.time()
sb.unreal = _U()
try:
    sb.build()
finally:
    sb.unreal = unreal
    sewer_boxcol.apply_level_later = _later
print("built in %.0f s" % (time.time() - t))
print("network actors:", len(sb.network_actors()))
