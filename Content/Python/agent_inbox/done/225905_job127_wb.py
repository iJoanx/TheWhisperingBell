import unreal
from collections import Counter, defaultdict
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
def layers(a):
    try: return [x.get_name() for x in a.get_editor_property('data_layer_assets') if x]
    except Exception: return []
wb = [a for a in acts if 'EDL_TheWhisperingBell' in layers(a)]
print("actors in EDL_TheWhisperingBell:", len(wb), Counter(a.get_class().get_name() for a in wb).most_common(12))
zero = [a for a in wb if abs(a.get_actor_location().x + 1800) < 0.5 and abs(a.get_actor_location().y + 500) < 0.5]
print("of those, were at 0,0 before tonight (now -1800,-500):", len(zero), Counter(a.get_class().get_name() for a in zero).most_common(8))
allzero = [a for a in acts if abs(a.get_actor_location().x + 1800) < 0.5 and abs(a.get_actor_location().y + 500) < 0.5]
print("whole level at -1800,-500:", len(allzero), "outside WB layer:", Counter(tuple(layers(a)) for a in allzero if a not in zero).most_common(6))
# mesh sharing for the zero ones
users = defaultdict(list)
for a in acts:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.static_mesh: users[c.static_mesh.get_path_name()].append(a)
shared = 0; samples = []
for a in zero:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.static_mesh:
            u = users[c.static_mesh.get_path_name()]
            if len(set(x.get_name() for x in u)) > 1:
                shared += 1
                if len(samples) < 6: samples.append((a.get_actor_label(), c.static_mesh.get_name(), len(u)))
print("zero-pivot meshes also used by other actors:", shared, samples)
rot = [a.get_actor_label() for a in zero if abs(a.get_actor_rotation().yaw) > 0.01 or abs(a.get_actor_scale3d().x - 1) > 1e-4]
print("zero-pivot actors with rotation/scale (not identity):", len(rot), rot[:6])
print("sample labels:", [a.get_actor_label() for a in zero[:12]])
print("other layer names:", Counter(l for a in acts for l in layers(a)).most_common())
