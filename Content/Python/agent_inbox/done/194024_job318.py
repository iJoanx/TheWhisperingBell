import unreal, time
lines = ["alive %s" % time.ctime()]
try:
    sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    lines.append("world %s" % sub.get_editor_world().get_name())
except Exception as e:
    lines.append("world err %s" % e)
try:
    dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    lines.append("dirty content packages: %d" % len(dirty))
    lines.append("dirty map packages: %d" % len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()))
except Exception as e:
    lines.append("dirty err %s" % e)
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump318.txt", "w").write("\n".join(lines))
