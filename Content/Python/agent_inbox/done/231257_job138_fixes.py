import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
D2 = unreal.Vector(5.07771 * 152.4, -9.91363 * 152.4, 0.0)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
# 1. Rag3: attached to a parent, so it moved twice each time; net it carries one extra D2
for a in acts:
    if a.get_actor_label() == 'Rag3':
        par = a.get_attach_parent_actor()
        a.modify(); a.root_component.modify()
        a.set_actor_location(a.get_actor_location() - D2, False, True)
        out.append("Rag3 parent=%s now at %s" % (par.get_actor_label() if par else None, a.get_actor_location()))
# 2. stop replicating movement on static interactables
ar = unreal.AssetRegistryHelpers.get_asset_registry()
bps = ar.get_assets(unreal.ARFilter(package_paths=["/Game/Level/WhisperingBell/Blueprints"], recursive_paths=True, class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "Blueprint")]))
changed = []
for ad in bps:
    n = str(ad.asset_name); p = "%s.%s" % (ad.package_name, n)
    try: cls = unreal.load_class(None, p + "_C")
    except Exception: continue
    if not cls: continue
    cdo = unreal.get_default_object(cls)
    try:
        if cdo.get_editor_property('replicate_movement'):
            setprops("%s.Default__%s_C" % (ad.package_name, n), {'bReplicateMovement': False})
            compile_bp(p); changed.append(n)
    except Exception as e: out.append("%s: %s" % (n, str(e)[:100]))
out.append("Replicate Movement turned off on %d blueprints: %s" % (len(changed), changed))
inst = 0
for a in eas.get_all_level_actors():
    if a.get_class().get_name()[:-2] in changed and a.get_editor_property('replicate_movement'):
        a.modify(); a.set_replicate_movement(False); inst += 1
out.append("placed instances that still overrode it: %d (fixed)" % inst)
print("\n".join(out))
