import sys, importlib, traceback, time
import unreal
out = []
GS = unreal.GeometryScript_AssetUtils
def mesh_tris(sm):
    dyn = unreal.DynamicMesh()
    read = unreal.GeometryScriptMeshReadLOD(); read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
    dyn, _ = GS.copy_mesh_from_static_mesh_v2(sm, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
    MQ = unreal.GeometryScript_MeshQueries
    fn = getattr(MQ, 'get_all_triangle_i_ds', None) or getattr(MQ, 'get_all_triangle_ids')
    ids = fn(dyn)
    if isinstance(ids, tuple): ids = [x for x in ids if isinstance(x, unreal.GeometryScriptIndexList)][0]
    ids = unreal.GeometryScript_List.convert_index_list_to_array(ids)
    tris = []
    for t in ids:
        r = unreal.GeometryScript_MeshQueries.get_triangle_positions(dyn, t)
        # returns (vertex1, vertex2, vertex3, is_valid) in some form
        vs = [v for v in r if isinstance(v, unreal.Vector)]
        if len(vs) == 3: tris.append(vs)
    return tris, dyn

MS = unreal.GeometryScript_MeshSpatial
def first(x, typ):
    if isinstance(x, typ): return x
    if isinstance(x, tuple):
        for v in x:
            if isinstance(v, typ): return v
    return None
def floor_z(dyn, bvh, x, y, ztop):
    r = MS.find_nearest_ray_intersection_with_mesh(dyn, bvh, unreal.Vector(x, y, ztop), unreal.Vector(0, 0, -1), unreal.GeometryScriptSpatialQueryOptions())
    h = first(r, unreal.GeometryScriptRayHitResult)
    if h is None or not h.get_editor_property('hit'): return None
    return h.get_editor_property('hit_position').z


try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    cam_loc, cam_rot = ues.get_level_viewport_camera_info()
    out.append("camera world %s rot %s" % (cam_loc, cam_rot))
    nd = [a for a in sb._actors() if a.get_actor_label() == "SL_303_Crossing"][0]
    T = nd.get_actor_transform()
    lc = unreal.MathLibrary.inverse_transform_location(T, cam_loc)
    out.append("crossing at %s yaw %.1f ; camera in crossing-local %s" % (nd.get_actor_location(), nd.get_actor_rotation().yaw, lc))
    fw = cam_rot.get_forward_vector()
    out.append("camera forward world %s, local %s" % (fw, unreal.MathLibrary.inverse_transform_direction(T, fw)))
    # actors whose bounds contain the area near the camera
    near = []
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        try:
            o, e = a.get_actor_bounds(False)
        except Exception:
            continue
        if all(abs(getattr(cam_loc, k) - getattr(o, k)) <= getattr(e, k) + 200 for k in 'xyz') and e.x < 20000:
            near.append("%s (%s) center %s ext %s" % (a.get_actor_label(), a.get_class().get_name(), o, e))
    out.append("actors around camera: %d" % len(near)); out += near[:40]
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing")
    tris, dyn = mesh_tris(sm)
    bvh = first(MS.build_bvh_for_mesh(dyn), unreal.GeometryScriptDynamicMeshBVH)
    def up_z(x, y, zb):
        r = MS.find_nearest_ray_intersection_with_mesh(dyn, bvh, unreal.Vector(x, y, zb), unreal.Vector(0, 0, 1), unreal.GeometryScriptSpatialQueryOptions())
        h = first(r, unreal.GeometryScriptRayHitResult)
        if h is None or not h.get_editor_property('hit'): return None
        return h.get_editor_property('hit_position').z
    layers = []; steps = []; grid = {}
    ztop = -120.0
    for yi in range(-450, 451, 5):
        for xi in range(-450, 451, 5):
            zt = floor_z(dyn, bvh, xi, yi, ztop)
            grid[(xi, yi)] = zt
            if zt is not None and zt < -185:
                zu = up_z(xi, yi, -260.0)
                if zu is not None and abs(zu - zt) > 0.05:
                    layers.append((round(zt - zu, 2), xi, yi, round(zt, 2), round(zu, 2)))
    for (xi, yi), z in grid.items():
        if z is None or z > -185: continue
        for (dx, dy) in ((5, 0), (0, 5)):
            z2 = grid.get((xi + dx, yi + dy))
            if z2 is None or z2 > -185: continue
            d = abs(z - z2)
            if d > 0.6: steps.append((round(d, 2), xi, yi, 'x' if dx else 'y', round(z, 2), round(z2, 2)))
    out.append("double layers (top-down vs bottom-up hit differ): %d" % len(layers))
    for L in sorted(layers, reverse=True)[:40]: out.append("layer " + str(L))
    out.append("channel-floor jumps > 0.6 cm between 5 cm neighbours: %d" % len(steps))
    for st in sorted(steps, reverse=True)[:80]: out.append("jump " + str(st))
    out.append("channel floor (z+200) every 20 cm:")
    for yi in range(440, -451, -20):
        row = []
        for xi in range(-440, 451, 20):
            z = grid.get((xi, yi))
            row.append('   .' if z is None or z > -185 else "%4.1f" % (z + 200))
        out.append("%+5d %s" % (yi, ''.join(row)))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump242.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
