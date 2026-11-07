import unreal, collections
out = []
world = unreal.EditorLevelLibrary.get_editor_world()
acts = unreal.GameplayStatics.get_all_actors_with_tag(world, 'RDL_Sewers')
out.append("RDL_Sewers actors loaded: %d" % len(acts))
groups = collections.Counter()
water_rows = []
def shading(m):
    try:
        b = m.get_base_material()
        return str(b.get_editor_property('shading_model')).split('.')[-1]
    except Exception as e: return '?'
for a in acts:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        mats = [m for m in c.get_materials() if m]
        key = (c.static_mesh.get_name() if c.static_mesh else None, tuple(sorted({m.get_name() for m in mats})))
        groups[key] += 1
        shs = {shading(m) for m in mats}
        names = ' '.join(m.get_name().lower() for m in mats) + ' ' + (c.static_mesh.get_name().lower() if c.static_mesh else '')
        if any('WATER' in s for s in shs) or any(k in names for k in ('water', 'sewage', 'liquid', 'sludge', 'muck')):
            t = c.get_world_transform(); r = t.rotation.rotator()
            lb = c.static_mesh.get_bounding_box() if c.static_mesh else None
            water_rows.append("%s | %s | comp=%s | mesh=%s | mats=%s | shading=%s | loc=(%d,%d,%d) rot=(r%.1f p%.1f y%.1f) scale=(%.2f,%.2f,%.2f) | localbox=%s | coll=%s" % (
                a.get_actor_label(), a.get_class().get_name(), c.get_name(), key[0], list(key[1]), shs,
                t.translation.x, t.translation.y, t.translation.z, r.roll, r.pitch, r.yaw, t.scale3d.x, t.scale3d.y, t.scale3d.z,
                ((round(lb.min.x), round(lb.min.y), round(lb.min.z)), (round(lb.max.x), round(lb.max.y), round(lb.max.z))) if lb else None,
                c.get_collision_profile_name()))
out.append("WATER-LIKE COMPONENTS: %d" % len(water_rows))
out.extend(water_rows[:200])
out.append("MESH/MATERIAL GROUPS (top 60):")
for k, n in groups.most_common(60): out.append("  %4d  %s  %s" % (n, k[0], list(k[1])))
# also check the sea plane's material shading model
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if a.get_actor_label() in ('WaterdeepWater',):
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            out.append("SEA %s mats=%s shading=%s" % (a.get_actor_label(), [m.get_name() for m in c.get_materials() if m], [shading(m) for m in c.get_materials() if m]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump195.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
