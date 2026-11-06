import unreal
from collections import Counter, defaultdict
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
def layers(a):
    try: return [x.get_name() for x in a.get_editor_property('data_layer_assets') if x]
    except Exception: return []
wb = [a for a in acts if 'EDL_TheWhisperingBell' in layers(a)]
z = [a for a in wb if abs(a.get_actor_location().x) < 0.5 and abs(a.get_actor_location().y) < 0.5]
print("WB actors at 0,0 now:", len(z), Counter(a.get_class().get_name() for a in z).most_common(6))
print("their Z values:", sorted(set(round(a.get_actor_location().z, 1) for a in z))[:10])
users = defaultdict(set)
for a in acts:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.static_mesh: users[c.static_mesh.get_path_name()].add(a.get_name())
sh = []
for a in z:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.static_mesh and len(users[c.static_mesh.get_path_name()]) > 1: sh.append((a.get_actor_label(), c.static_mesh.get_name(), len(users[c.static_mesh.get_path_name()])))
print("of those, meshes shared with other actors:", len(sh), sh[:8])
print("rotated/scaled:", [a.get_actor_label() for a in z if abs(a.get_actor_rotation().yaw) > 0.01 or abs(a.get_actor_rotation().pitch) > 0.01 or abs(a.get_actor_rotation().roll) > 0.01 or abs(a.get_actor_scale3d().x - 1) > 1e-4][:8])
print("sample:", [(a.get_actor_label(), a.get_class().get_name()) for a in z[:15]])
nz = [a for a in wb if a not in z]
print("WB not at 0,0:", len(nz), Counter(a.get_class().get_name() for a in nz).most_common(8))
allz = [a for a in acts if abs(a.get_actor_location().x) < 0.5 and abs(a.get_actor_location().y) < 0.5 and a not in z]
print("other (non-WB) actors at 0,0:", len(allz), Counter(tuple(layers(a)) for a in allz).most_common(5))
