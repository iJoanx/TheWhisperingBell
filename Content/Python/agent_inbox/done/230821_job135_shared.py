import unreal
from collections import defaultdict
D = unreal.Vector(-9.91363 * 152.4, 5.07771 * 152.4, 0.0)
A = unreal.GeometryScript_AssetUtils; T = unreal.GeometryScript_MeshTransforms; C = unreal.GeometryScript_Collision
eal = unreal.EditorAssetLibrary; sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
def layers(a):
    try: return [x.get_name() for x in a.get_editor_property('data_layer_assets') if x]
    except Exception: return []
users = defaultdict(list)
for a in acts:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.static_mesh: users[c.static_mesh.get_path_name()].append((a, c))
zero = [a for a in acts if 'EDL_TheWhisperingBell' in layers(a) and abs(a.get_actor_location().x) < 0.01 and abs(a.get_actor_location().y) < 0.01 and a.get_class().get_name() == 'StaticMeshActor']
baked = {}
for a in zero:
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if c and c.static_mesh: baked[c.static_mesh.get_path_name()] = (a, c)
shared = {p: [u for u in users[p] if u[0] != baked[p][0]] for p in baked if len(users[p]) > 1}
print("baked meshes with other users:", {p.split('.')[-1]: [u[0].get_actor_label() for u in v] for p, v in shared.items()})
lod = unreal.GeometryScriptMeshReadLOD(); lod.set_editor_property('lod_type', unreal.GeometryScriptLODType.SOURCE_MODEL); lod.set_editor_property('lod_index', 0)
wl = unreal.GeometryScriptMeshWriteLOD(); wl.set_editor_property('lod_index', 0)
wo = unreal.GeometryScriptCopyMeshToAssetOptions()
for k, v in (('replace_materials', False), ('enable_recompute_normals', False), ('enable_recompute_tangents', False), ('apply_nanite_settings', False), ('emit_transaction', False)):
    try: wo.set_editor_property(k, v)
    except Exception: pass
def shift(sm, d):
    bs = sme.get_lod_build_settings(sm, 0)
    has = C.get_simple_collision_shape_count(C.get_simple_collision_from_static_mesh(sm)) > 0
    sc = C.get_simple_collision_from_static_mesh(sm) if has else None
    dm = unreal.DynamicMesh(); A.copy_mesh_from_static_mesh_v2(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), lod)
    T.translate_mesh(dm, d); A.copy_mesh_to_static_mesh(dm, sm, wo, wl); sme.set_lod_build_settings(sm, 0, bs)
    if has:
        sc2 = C.transform_simple_collision_shapes(sc, unreal.Transform(d, unreal.Rotator(0, 0, 0), unreal.Vector(1, 1, 1)), unreal.GeometryScriptTransformCollisionOptions())
        C.set_simple_collision_of_static_mesh(sc2[0] if isinstance(sc2, tuple) else sc2, sm, unreal.GeometryScriptSetSimpleCollisionOptions())
for p, others in shared.items():
    za, zc = baked[p]
    if p.endswith('_Origin.' + p.split('.')[-1]): continue
    pkg = p.split('.')[0]
    newp = pkg + '_Origin'
    nm = unreal.load_asset(newp) if eal.does_asset_exist(newp) else eal.duplicate_asset(pkg, newp)   # copy keeps the baked geometry
    za.modify(); zc.modify(); zc.set_static_mesh(nm)
    shift(zc.static_mesh if False else unreal.load_asset(pkg), unreal.MathLibrary.inverse_transform_direction(za.get_actor_transform(), D) * -1.0)   # restore original
    print("%s: 0,0 actor now uses %s; original restored for %s" % (p.split('.')[-1], nm.get_name(), [u[0].get_actor_label() for u in others]))
# Rag3 was moved back once; now that its mesh is restored it needs the normal offset again
for a in acts:
    if a.get_actor_label() == 'Rag3':
        a.modify(); a.root_component.modify(); a.set_actor_location(a.get_actor_location() + D, False, True); print("Rag3 ->", a.get_actor_location())
# simple vs complex collision at points where complex was hit
ok = n = 0; bad = []
for a in zero[:80]:
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if not c or c.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION: continue
    bs = c.static_mesh.get_editor_property('body_setup')
    if 'COMPLEX_AS_SIMPLE' in str(bs.get_editor_property('collision_trace_flag')): continue
    if C.get_simple_collision_shape_count(C.get_simple_collision_from_static_mesh(c.static_mesh)) == 0: continue
    o, e = a.get_actor_bounds(False)
    rc = c.line_trace_component(o + unreal.Vector(0, 0, e.z + 50), o - unreal.Vector(0, 0, e.z + 50), True, False, False)
    if not (rc and rc[0]): continue
    hp = rc[1] if len(rc) > 1 else None
    rs = c.line_trace_component(o + unreal.Vector(0, 0, e.z + 50), o - unreal.Vector(0, 0, e.z + 50), False, False, False)
    n += 1
    if rs and rs[0]: ok += 1
    else: bad.append(a.get_actor_label())
    if n >= 30: break
print("simple collision present where the visible mesh is: %d of %d; missing: %s" % (ok, n, bad[:10]))
print("dirty content:", len(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()))
