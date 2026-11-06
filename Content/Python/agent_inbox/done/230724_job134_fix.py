import unreal
D = unreal.Vector(-9.91363 * 152.4, 5.07771 * 152.4, 0.0)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
r = [a for a in acts if a.get_actor_label() == 'Rag3'][0]
c = r.get_component_by_class(unreal.StaticMeshComponent)
users = [a.get_actor_label() for a in acts for cc in a.get_components_by_class(unreal.StaticMeshComponent) if c and cc.static_mesh == c.static_mesh]
print("Rag3 mesh", c.static_mesh.get_name() if c else None, "used by", users, "rot", r.get_actor_rotation(), "scale", r.get_actor_scale3d())
r.modify(); r.root_component.modify()
r.set_actor_location(r.get_actor_location() - D, False, True)
print("Rag3 location now", r.get_actor_location())
# collision check on several baked actors: trace straight at each component's own bounds centre
zero = [a for a in acts if abs(a.get_actor_location().x) < 0.01 and abs(a.get_actor_location().y) < 0.01 and a.get_class().get_name() == 'StaticMeshActor']
checked = hit = 0; miss = []
for a in zero:
    cc = a.get_component_by_class(unreal.StaticMeshComponent)
    if not cc or cc.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION: continue
    o, e = a.get_actor_bounds(False)
    if e.z < 1 and e.x < 1: continue
    checked += 1
    res = cc.line_trace_component(o + unreal.Vector(0, 0, e.z + 50), o - unreal.Vector(0, 0, e.z + 50), True, False, False)
    if res and res[0]: hit += 1
    else: miss.append(a.get_actor_label())
    if checked >= 40: break
print("component traces through the middle of baked meshes: %d of %d hit (misses can be open shapes like railings): %s" % (hit, checked, miss[:10]))
