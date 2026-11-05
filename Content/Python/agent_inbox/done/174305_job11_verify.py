import unreal
import sewer_builder as sb
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
nodes = [a for a in eas.get_all_level_actors() if sb._is_node(a)]
none, cnt, nomesh = [], 0, 0
for n in nodes:
    if sb._is_end(sb._node_type(n)):
        continue
    c = n.get_component_by_class(unreal.StaticMeshComponent)
    sm = c.get_editor_property("static_mesh") if c else None
    if not sm:
        nomesh += 1; continue
    k = len(sm.get_editor_property("body_setup").get_editor_property("agg_geom").get_editor_property("convex_elems"))
    cnt += 1
    if k == 0:
        none.append(n.get_actor_label())
print("node meshes:", cnt, "without mesh:", nomesh, "without collision:", len(none), none[:20])
print("dirty maps:", [str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
print("dirty content:", len(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()))
