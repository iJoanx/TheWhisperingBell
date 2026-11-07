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
    n, failed = sb.rebake_crossings(["SL_303_Crossing"])
    out.append("rebaked %d, failed %s" % (n, failed))
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing")
    tris, dyn = mesh_tris(sm)
    bvh = first(MS.build_bvh_for_mesh(dyn), unreal.GeometryScriptDynamicMeshBVH)
    out.append("SL_303 floor height map (mesh-local, 10 cm grid, x right, y up). '.'=walkway z 0, digits=cm BELOW walkway, '+'=above, '#'=channel, ' '=no floor")
    R, S = 460, 10
    for yi in range(R, -R - 1, -S):
        row = ''
        for xi in range(-R, R + 1, S):
            z = floor_z(dyn, bvh, xi, yi, 30.0)
            if z is None: row += ' '
            elif z < -40: row += '#'
            elif abs(z) < 0.3: row += '.'
            elif z > 0: row += '+'
            else:
                d = int(round(-z))
                row += str(d) if d < 10 else ('a' if d < 20 else 'b')
        out.append("%+5d %s" % (yi, row))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump236.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
