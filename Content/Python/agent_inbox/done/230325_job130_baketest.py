import unreal
D = unreal.Vector(-9.91363 * 152.4, 5.07771 * 152.4, 0.0)
A = unreal.GeometryScript_AssetUtils; T = unreal.GeometryScript_MeshTransforms; C = unreal.GeometryScript_Collision
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
src = [a for a in eas.get_all_level_actors() if a.get_actor_label() == 'WB_F3_Floor'][0].get_component_by_class(unreal.StaticMeshComponent).static_mesh
tmp = '/Game/__AgentTemp/BakeTest_' + src.get_name()
if eal.does_asset_exist(tmp): eal.delete_asset(tmp)
m = eal.duplicate_asset(src.get_path_name().split('.')[0], tmp)
def stats(sm):
    bb = sm.get_bounding_box()
    sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    return dict(min=(round(bb.min.x, 2), round(bb.min.y, 2), round(bb.min.z, 2)), max=(round(bb.max.x, 2), round(bb.max.y, 2), round(bb.max.z, 2)),
                tris=sme.get_number_verts(sm, 0), mats=len(sm.static_materials), uvs=sme.get_num_uv_channels(sm, 0),
                lmuv=sm.get_editor_property('light_map_coordinate_index'))
def coll(sm):
    sc = C.get_simple_collision_from_static_mesh(sm)
    sc = sc[0] if isinstance(sc, tuple) else sc
    try: return C.get_simple_collision_shape_count(sc)
    except Exception as e: return "?%s" % e
print("before", stats(m), "collision shapes", coll(m))
bs = m.get_editor_property('body_setup'); ag = bs.get_editor_property('agg_geom')
print("convex0 before:", ag.get_editor_property('convex_elems')[0].get_editor_property('elem_box') if ag.get_editor_property('convex_elems') else None)
dm = unreal.DynamicMesh()
ro = unreal.GeometryScriptCopyMeshFromAssetOptions()
lod = unreal.GeometryScriptMeshReadLOD(); lod.set_editor_property('lod_type', unreal.GeometryScriptLODType.SOURCE_MODEL); lod.set_editor_property('lod_index', 0)
r = A.copy_mesh_from_static_mesh_v2(m, dm, ro, lod)
print("copy from:", r[1] if isinstance(r, tuple) else r)
sc = C.get_simple_collision_from_static_mesh(m); sc = sc[0] if isinstance(sc, tuple) else sc
T.translate_mesh(dm, D)
xf = unreal.Transform(D, unreal.Rotator(0, 0, 0), unreal.Vector(1, 1, 1))
sc2 = C.transform_simple_collision_shapes(sc, xf, unreal.GeometryScriptTransformCollisionOptions())
sc2 = sc2[0] if isinstance(sc2, tuple) else sc2
wo = unreal.GeometryScriptCopyMeshToAssetOptions()
for k, v in (('replace_materials', False), ('enable_recompute_normals', False), ('enable_recompute_tangents', False), ('apply_nanite_settings', False), ('emit_transaction', False)):
    try: wo.set_editor_property(k, v)
    except Exception as e: print("opt", k, e)
wl = unreal.GeometryScriptMeshWriteLOD(); wl.set_editor_property('lod_index', 0)
r2 = A.copy_mesh_to_static_mesh(dm, m, wo, wl)
print("copy to:", r2[1] if isinstance(r2, tuple) else r2)
r3 = C.set_simple_collision_of_static_mesh(sc2, m, unreal.GeometryScriptSetSimpleCollisionOptions())
print("set collision:", r3)
print("after ", stats(m), "collision shapes", coll(m))
ag = m.get_editor_property('body_setup').get_editor_property('agg_geom')
print("convex0 after:", ag.get_editor_property('convex_elems')[0].get_editor_property('elem_box') if ag.get_editor_property('convex_elems') else None)
print("expected shift:", D)
