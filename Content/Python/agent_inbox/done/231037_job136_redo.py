import unreal, sys
from collections import defaultdict
OUT = r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\redo136.txt"
log = []
def P(s):
    log.append(str(s)); open(OUT, "w", encoding="utf-8").write("\n".join(log))
D1 = unreal.Vector(-9.91363 * 152.4, 5.07771 * 152.4, 0.0)     # applied by mistake
D2 = unreal.Vector(5.07771 * 152.4, -9.91363 * 152.4, 0.0)     # wanted
DL = D2 - D1
A = unreal.GeometryScript_AssetUtils; T = unreal.GeometryScript_MeshTransforms; C = unreal.GeometryScript_Collision
eal = unreal.EditorAssetLibrary; sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
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
    dm = unreal.DynamicMesh()
    r = A.copy_mesh_from_static_mesh_v2(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), lod)
    if (r[1] if isinstance(r, tuple) else r) != unreal.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('read failed')
    T.translate_mesh(dm, d)
    r = A.copy_mesh_to_static_mesh(dm, sm, wo, wl)
    if (r[1] if isinstance(r, tuple) else r) != unreal.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('write failed')
    sme.set_lod_build_settings(sm, 0, bs)
    if has:
        sc2 = C.transform_simple_collision_shapes(sc, unreal.Transform(d, unreal.Rotator(0, 0, 0), unreal.Vector(1, 1, 1)), unreal.GeometryScriptTransformCollisionOptions())
        C.set_simple_collision_of_static_mesh(sc2[0] if isinstance(sc2, tuple) else sc2, sm, unreal.GeometryScriptSetSimpleCollisionOptions())
def local(a, v): return unreal.MathLibrary.inverse_transform_direction(a.get_actor_transform(), v)
def layers(a):
    try: return [x.get_name() for x in a.get_editor_property('data_layer_assets') if x]
    except Exception: return []
acts = eas.get_all_level_actors()
wb = [a for a in acts if 'EDL_TheWhisperingBell' in layers(a)]
Z = [a for a in wb if abs(a.get_actor_location().x) < 0.5 and abs(a.get_actor_location().y) < 0.5 and a.get_class().get_name() == 'StaticMeshActor']
O = [a for a in wb if a not in Z]
P("WB %d: pivots at 0,0 %d, others %d; extra shift %s" % (len(wb), len(Z), len(O), DL))
users = defaultdict(list)
for a in acts:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.static_mesh: users[c.static_mesh.get_path_name()].append((a, c))
# 1) baked meshes that other actors also use: give the 0,0 actor its own copy, restore the original for the rest
for a in Z:
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    p = c.static_mesh.get_path_name()
    others = [u for u in users[p] if u[0] != a]
    if not others: continue
    pkg = p.split('.')[0]; newp = pkg + '_Origin'
    nm = unreal.load_asset(newp) if eal.does_asset_exist(newp) else eal.duplicate_asset(pkg, newp)
    a.modify(); c.modify(); c.set_static_mesh(nm)
    shift(unreal.load_asset(pkg), local(a, D1) * -1.0)
    P("shared %s: %s gets %s; original restored for %s" % (pkg.split('/')[-1], a.get_actor_label(), nm.get_name(), [u[0].get_actor_label() for u in others]))
# Rag3 got one extra +D1 earlier (moved +D1, -D1, +D1, i.e. +D1 net) - already consistent with the others now that its mesh is restored.
before = {a.get_name(): a.get_actor_bounds(False)[0] for a in wb}
# 2) bake the extra shift into every 0,0 mesh
ok = 0; fails = []; seen = set()
for a in Z:
    c = a.get_component_by_class(unreal.StaticMeshComponent); sm = c.static_mesh
    if sm.get_path_name() in seen: fails.append(a.get_actor_label()); continue
    try: shift(sm, local(a, DL)); seen.add(sm.get_path_name()); ok += 1
    except Exception as e: fails.append((a.get_actor_label(), str(e)[:100]))
P("re-baked %d, failed %s" % (ok, fails[:10]))
# 3) move the rest
for a in O:
    a.modify(); a.root_component.modify(); a.set_actor_location(a.get_actor_location() + DL, False, True)
P("moved %d" % len(O))
# 4) checks
bad = []
for a in wb:
    dv = a.get_actor_bounds(False)[0] - before[a.get_name()]
    if abs(dv.x - DL.x) > 1 or abs(dv.y - DL.y) > 1 or abs(dv.z) > 1: bad.append((a.get_actor_label(), round(dv.x, 1), round(dv.y, 1)))
P("bounds shifted by the extra offset: %d of %d; off: %s" % (len(wb) - len(bad), len(wb), bad[:10]))
P("pivots still at 0,0: %d of %d" % (sum(1 for a in Z if abs(a.get_actor_location().x) < 0.01 and abs(a.get_actor_location().y) < 0.01), len(Z)))
for lab in ('Rag2', 'Rag3', 'WB_P_Rag', 'WB_P_Rug', 'WB_P_Rug2'):
    for a in wb:
        if a.get_actor_label() == lab:
            c = a.get_component_by_class(unreal.StaticMeshComponent)
            P("  %s loc %s mesh %s" % (lab, a.get_actor_location(), c.static_mesh.get_name() if c else None))
P("dirty content %d, maps %d" % (len(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()), len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())))
