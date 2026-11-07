import unreal, collections
out = []
world = unreal.EditorLevelLibrary.get_editor_world()
meshes = collections.OrderedDict()
for a in unreal.GameplayStatics.get_all_actors_with_tag(world, 'RDL_Sewers'):
    for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
        if unreal.Name('Water_Sewage') in list(c.component_tags):
            m = c.get_editor_property('static_mesh')
            meshes.setdefault(m.get_path_name(), [m, 0, c.get_name()])[1] += c.get_instance_count()
out.append("distinct water meshes: %d" % len(meshes))
flat = sloped = 0
for p, (m, n, cn) in meshes.items():
    b = m.get_bounding_box()
    dz = b.max.z - b.min.z
    if dz < 0.5: flat += 1
    else: sloped += 1
    if 'SL_303' in p or dz >= 0.5 and sloped <= 8:
        out.append("%-60s instances=%d zrange=%.1f (%.1f..%.1f) comp=%s" % (p.split('/')[-1], n, dz, b.min.z, b.max.z, cn))
out.append("flat meshes: %d, not flat: %d" % (flat, sloped))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump218.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
