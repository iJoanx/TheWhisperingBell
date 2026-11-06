import unreal
from collections import Counter
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
print("loaded actors:", len(acts))
c = Counter(a.get_class().get_name() for a in acts)
print("classes:", c.most_common(30))
ws = w.get_world_settings()
for p in ('kill_z', 'enable_world_bounds_checks', 'kill_z_damage_type'):
    try: print(p, ws.get_editor_property(p))
    except Exception as e: print(p, "?")
wp = None
try:
    wp = w.get_world_partition() if hasattr(w, 'get_world_partition') else None
except Exception: pass
print("world partition:", wp)
# actor descriptors (all actors incl. unloaded)
try:
    sub = unreal.get_editor_subsystem(unreal.WorldPartitionEditorSubsystem) if hasattr(unreal, 'WorldPartitionEditorSubsystem') else None
    print("WP editor subsystem:", sub, [n for n in dir(sub) if not n.startswith('_')][:40] if sub else None)
except Exception as e: print("wpsub err", e)
import os, glob
ext = r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\__ExternalActors__\Levels\PersistentLevel_WP"
n = sum(1 for _ in glob.iglob(ext + r"\**\*.uasset", recursive=True))
print("external actor files on disk:", n)
spatial = sum(1 for a in acts if a.get_editor_property('is_spatially_loaded'))
print("spatially loaded among loaded:", spatial)
lands = [a for a in acts if 'Landscape' in a.get_class().get_name()]
print("landscape actors:", [(a.get_actor_label(), a.get_class().get_name()) for a in lands][:10])
attached = sum(1 for a in acts if a.get_attach_parent_actor())
print("actors attached to another actor:", attached)
mob = Counter(str(a.root_component.get_editor_property('mobility')) if a.root_component else 'none' for a in acts)
print("root mobility:", mob)
