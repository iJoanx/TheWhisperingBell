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
    nodes = [a for a in sb._actors() if sb._is_node(a)]
    _, per = sb._gather(nodes, [])
    nd = [a for a in nodes if a.get_actor_label() == "SL_303_Crossing"][0]
    conns = sb._local_conns(nd, per[nd.get_path_name()])
    for k in range(len(conns)):
        out.append("arm %d pitch %.2f corners (s,t) left/right: %s" % (k, conns[k]["pitch"], sb._arm_corner_line(conns, k)))
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing")
    tris, dyn = mesh_tris(sm)
    bvh = first(MS.build_bvh_for_mesh(dyn), unreal.GeometryScriptDynamicMeshBVH)
    R, S = 460, 10
    grid = {}
    for yi in range(R, -R - 1, -S):
        for xi in range(-R, R + 1, S):
            grid[(xi, yi)] = floor_z(dyn, bvh, xi, yi, 30.0)
    zs = [z for z in grid.values() if z is not None and z < -40]
    zmin = min(zs); zmax = max(zs)
    out.append("channel floor z range %.1f .. %.1f" % (zmin, zmax))
    out.append("CHANNEL floor map: digit = cm above the lowest channel point (a=10-19,b=20-29,c=30+ up to -40), '.'=walkway level band, ' '=none")
    for yi in range(R, -R - 1, -S):
        row = ''
        for xi in range(-R, R + 1, S):
            z = grid[(xi, yi)]
            if z is None: row += ' '
            elif z >= -40: row += '.'
            else:
                d = int(round(z - zmin))
                row += str(d) if d < 10 else ('a' if d < 20 else ('b' if d < 30 else 'c'))
        out.append("%+5d %s" % (yi, row))
    # step detector: small sudden jumps (0.4-25 cm over 4 cm) anywhere on floors
    steps = []
    for yi in range(R, -R - 1, -S):
        for xi in range(-R, R + 1, S):
            for (dx, dy) in ((2, 0), (0, 2)):
                z1 = floor_z(dyn, bvh, xi - dx, yi - dy, 30.0); z2 = floor_z(dyn, bvh, xi + dx, yi + dy, 30.0)
                if z1 is None or z2 is None: continue
                d = abs(z1 - z2)
                if 0.4 < d < 25: steps.append((d, xi, yi, 'x' if dx else 'y', z1, z2))
    steps.sort(reverse=True)
    out.append("steps found: %d" % len(steps))
    for st in steps[:60]: out.append("step %.2f cm at (%d,%d) across %s  z %.1f / %.1f" % st)
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump239.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
