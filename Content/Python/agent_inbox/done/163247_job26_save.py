# Save what the sewer rebuild changed, and nothing that was already unsaved before it.
import unreal, json, os
PY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
before = set(json.load(open(os.path.join(PY, "agent_inbox", "dirty_before_sewers.json"))))
U = unreal.EditorLoadingAndSavingUtils
dirty = list(U.get_dirty_map_packages()) + list(U.get_dirty_content_packages())
mine = [p for p in dirty if str(p.get_name()) not in before]
kinds = {}
for p in mine:
    n = str(p.get_name())
    k = "external actors" if "__ExternalActors__" in n else ("world" if n.startswith("/Game/Levels/") else n.rsplit("/", 1)[0])
    kinds[k] = kinds.get(k, 0) + 1
print("to save:", len(mine), kinds)
print("left unsaved (yours from before):", len([p for p in dirty if str(p.get_name()) in before]))
ok = U.save_packages(mine, True)
print("saved:", ok)
after = set(str(p.get_name()) for p in list(U.get_dirty_map_packages()) + list(U.get_dirty_content_packages()))
still = sorted(after - before)
print("still unsaved from the rebuild:", len(still), still[:10])
