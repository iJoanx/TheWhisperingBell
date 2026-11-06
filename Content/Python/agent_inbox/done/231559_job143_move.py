import unreal, sys
from collections import defaultdict
OUT = r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\move143.txt"
log = []
def P(s):
    log.append(str(s)); open(OUT, "w", encoding="utf-8").write("\n".join(log))
DL = unreal.Vector(-2 * 5.07771 * 152.4, 2 * 9.91363 * 152.4, 0.0)   # user: -1547.68 X, +3021.68 Y from here
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
skip = set()
for a in Z:
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    others = [u[0].get_actor_label() for u in users[c.static_mesh.get_path_name()] if u[0] != a]
    if others: skip.add(a.get_name()); P("NOT baking %s: mesh also used by %s" % (a.get_actor_label(), others))
before = {a.get_name(): a.get_actor_bounds(False)[0] for a in wb}
# 2) bake the extra shift into every 0,0 mesh
ok = 0; fails = []; seen = set()
for a in Z:
    if a.get_name() in skip: continue
    c = a.get_component_by_class(unreal.StaticMeshComponent); sm = c.static_mesh
    if sm.get_path_name() in seen: fails.append(a.get_actor_label()); continue
    try: shift(sm, local(a, DL)); seen.add(sm.get_path_name()); ok += 1
    except Exception as e: fails.append((a.get_actor_label(), str(e)[:100]))
P("re-baked %d, failed %s" % (ok, fails[:10]))
# 3) move the rest
att = [a.get_actor_label() for a in O if a.get_attach_parent_actor() is not None]
P('attached (follow their parent, not moved directly): %s' % att)
for a in O:
    if a.get_attach_parent_actor() is not None: continue
    a.modify(); a.root_component.modify(); a.set_actor_location(a.get_actor_location() + DL, False, True)
P("moved %d" % len(O))
# 4) checks
bad = []
for a in wb:
    dv = a.get_actor_bounds(False)[0] - before[a.get_name()]
    if abs(dv.x - DL.x) > 1 or abs(dv.y - DL.y) > 1 or abs(dv.z) > 1: bad.append((a.get_actor_label(), round(dv.x, 1), round(dv.y, 1)))
P("bounds shifted by the extra offset: %d of %d; off: %s" % (len(wb) - len(bad), len(wb), bad[:10]))
P("pivots still at 0,0: %d of %d" % (sum(1 for a in Z if abs(a.get_actor_location().x) < 0.01 and abs(a.get_actor_location().y) < 0.01), len(Z)))
for lab in ('Rag3', 'WB_P_Rug', 'WB_F3_Floor'):
    for a in wb:
        if a.get_actor_label() == lab:
            c = a.get_component_by_class(unreal.StaticMeshComponent)
            P("  %s loc %s mesh %s" % (lab, a.get_actor_location(), c.static_mesh.get_name() if c else None))
P("dirty content %d, maps %d" % (len(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()), len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())))
