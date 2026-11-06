import unreal, sys, time
t0 = time.time()
D = unreal.Vector(-9.91363 * 152.4, 5.07771 * 152.4, 0.0)
A = unreal.GeometryScript_AssetUtils; T = unreal.GeometryScript_MeshTransforms; C = unreal.GeometryScript_Collision
eal = unreal.EditorAssetLibrary
sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
OUT = r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\wbmove133.txt"
log = []
def P(s):
    log.append(str(s)); open(OUT, "w", encoding="utf-8").write("\n".join(log))
def layers(a):
    try: return [x.get_name() for x in a.get_editor_property('data_layer_assets') if x]
    except Exception: return []
acts = eas.get_all_level_actors()
wb = [a for a in acts if 'EDL_TheWhisperingBell' in layers(a)]
zero = [a for a in wb if abs(a.get_actor_location().x) < 0.5 and abs(a.get_actor_location().y) < 0.5]
others = [a for a in wb if a not in zero]
P("WB %d: bake %d, move %d" % (len(wb), len(zero), len(others)))
def wbounds(a):
    o, e = a.get_actor_bounds(False); return o
before = {a.get_name(): wbounds(a) for a in wb}
# rug: give the 0,0 rug its own mesh copy
for a in zero:
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if c and c.static_mesh and c.static_mesh.get_name() == 'WB_P_Rug':
        pth = c.static_mesh.get_path_name().split('.')[0]
        newp = pth + '_Origin'
        nm = unreal.load_asset(newp) if eal.does_asset_exist(newp) else eal.duplicate_asset(pth, newp)
        a.modify(); c.modify(); c.set_static_mesh(nm)
        P("rug: %s now uses %s" % (a.get_actor_label(), nm.get_name()))
lod = unreal.GeometryScriptMeshReadLOD(); lod.set_editor_property('lod_type', unreal.GeometryScriptLODType.SOURCE_MODEL); lod.set_editor_property('lod_index', 0)
wl = unreal.GeometryScriptMeshWriteLOD(); wl.set_editor_property('lod_index', 0)
wo = unreal.GeometryScriptCopyMeshToAssetOptions()
for k, v in (('replace_materials', False), ('enable_recompute_normals', False), ('enable_recompute_tangents', False), ('apply_nanite_settings', False), ('emit_transaction', False)):
    try: wo.set_editor_property(k, v)
    except Exception: pass
ok = 0; fails = []; done = set()
for a in zero:
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    sm = c.static_mesh if c else None
    if sm is None: fails.append((a.get_actor_label(), 'no mesh')); continue
    if sm.get_path_name() in done: fails.append((a.get_actor_label(), 'mesh already baked for another actor')); continue
    try:
        d = unreal.MathLibrary.inverse_transform_direction(a.get_actor_transform(), D)
        bsets = sme.get_lod_build_settings(sm, 0)
        has_simple = C.get_simple_collision_shape_count(C.get_simple_collision_from_static_mesh(sm)) > 0
        sc = C.get_simple_collision_from_static_mesh(sm) if has_simple else None
        dm = unreal.DynamicMesh()
        r = A.copy_mesh_from_static_mesh_v2(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), lod)
        if (r[1] if isinstance(r, tuple) else r) != unreal.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('copy from failed')
        T.translate_mesh(dm, d)
        r = A.copy_mesh_to_static_mesh(dm, sm, wo, wl)
        if (r[1] if isinstance(r, tuple) else r) != unreal.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('copy to failed')
        sme.set_lod_build_settings(sm, 0, bsets)
        if has_simple:
            sc2 = C.transform_simple_collision_shapes(sc, unreal.Transform(d, unreal.Rotator(0, 0, 0), unreal.Vector(1, 1, 1)), unreal.GeometryScriptTransformCollisionOptions())
            sc2 = sc2[0] if isinstance(sc2, tuple) else sc2
            C.set_simple_collision_of_static_mesh(sc2, sm, unreal.GeometryScriptSetSimpleCollisionOptions())
        done.add(sm.get_path_name()); ok += 1
    except Exception as e:
        fails.append((a.get_actor_label(), str(e)[:150]))
    if ok % 25 == 0: P("baked %d (%.0fs)" % (ok, time.time() - t0))
P("baked %d, failed %d %s" % (ok, len(fails), fails[:10]))
for a in others:
    a.modify(); a.root_component.modify()
    a.set_actor_location(a.get_actor_location() + D, False, True)
P("moved %d actors" % len(others))
# verify: every WB actor's world bounds should have shifted by D
bad = []
for a in wb:
    o = wbounds(a); b = before[a.get_name()]
    dv = o - b
    if abs(dv.x - D.x) > 1.0 or abs(dv.y - D.y) > 1.0 or abs(dv.z) > 1.0: bad.append((a.get_actor_label(), round(dv.x, 1), round(dv.y, 1), round(dv.z, 1)))
P("bounds check: %d of %d shifted by exactly the offset; off: %s" % (len(wb) - len(bad), len(wb), bad[:12]))
P("zero-pivot actors still at 0,0: %d" % sum(1 for a in zero if abs(a.get_actor_location().x) < 0.01 and abs(a.get_actor_location().y) < 0.01))
# collision check: trace down onto the floor's new middle
fl = [a for a in zero if a.get_actor_label() == 'WB_F3_Floor']
if fl:
    o, e = fl[0].get_actor_bounds(False)
    hit = unreal.SystemLibrary.line_trace_single(fl[0], o + unreal.Vector(0, 0, 500), o - unreal.Vector(0, 0, 500), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    h = hit.to_tuple() if hit else None
    P("trace at WB_F3_Floor centre hits: %s" % (h[9].get_actor_label() if h and h[0] and h[9] else None))
w = sys.modules.get('walls_spline')
if w:
    for a in eas.get_all_level_actors():
        if w._is_wall(a): w._STATE["sig"][a.get_path_name()] = w._signature(a)
P("dirty maps %d, dirty content %d, %.0fs" % (len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()), len(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()), time.time() - t0))
