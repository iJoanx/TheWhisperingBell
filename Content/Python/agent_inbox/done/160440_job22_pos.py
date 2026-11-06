import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
nodes = {a.get_actor_label(): a for a in eas.get_all_level_actors() if a.get_class().get_name() == "BP_SewerNode_C"}
for k in sorted(nodes)[:12]:
    l = nodes[k].get_actor_location(); s = nodes[k].get_actor_scale3d()
    print(k, round(l.x, 1), round(l.y, 1), round(l.z, 1), "scale", round(s.x, 3))
net = [a for a in eas.get_all_level_actors() if a.get_actor_label() == "SewerNetwork_GENERATED"][0]
print("network at", net.get_actor_location(), net.get_actor_scale3d(), net.get_actor_rotation())
