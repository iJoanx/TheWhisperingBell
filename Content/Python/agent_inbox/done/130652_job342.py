import unreal, collections, math, json
APPLY = 'ALL'          # 'ONE' = dry run for all + write only the first tower; 'ALL' = write every tower
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump342.txt", "w", encoding="utf-8").write("\n".join(out))
GA, GQ, GU = unreal.GeometryScript_AssetUtils, unreal.GeometryScript_MeshQueries, unreal.GeometryScript_UVs
def load_dm(sm):
    dm = unreal.DynamicMesh()
    GA.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    return dm
def tri_uvs(dm, ch, t):
    r = GQ.get_triangle_u_vs(dm, ch, t)
    return [x for x in r if isinstance(x, unreal.Vector2D)]
def code_of(dm):
    c = collections.Counter()
    n = GQ.get_num_triangle_i_ds(dm)
    for t in range(0, n, max(1, n // 30)):
        u = tri_uvs(dm, 5, t)
        if u: c[int(round(u[0].x))] += 1
    return c.most_common(1)[0][0] if c else None
try:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    towers, houses = {}, []
    for a in eas.get_all_level_actors():
        if not isinstance(a, unreal.StaticMeshActor): continue
        sm = a.static_mesh_component.static_mesh
        if not sm: continue
        n = sm.get_name()
        if n.startswith('SM_Towers') or n.startswith('SM_Houses'):
            o, e = a.get_actor_bounds(False)
            (towers.__setitem__(n, (sm, o)) if n.startswith('SM_Towers') else houses.append((sm, o)))
    out.append("placed towers %d, houses %d" % (len(towers), len(houses)))
    hcache = {}
    plan = []
    for n in sorted(towers):
        sm, o = towers[n]
        dm = load_dm(sm)
        code = code_of(dm)
        if code is None or code % 16 != 0: continue          # has a ward already
        near = sorted(houses, key=lambda h: (h[1].x - o.x) ** 2 + (h[1].y - o.y) ** 2)[:7]
        wards = collections.Counter()
        for hsm, ho in near:
            k = hsm.get_name()
            if k not in hcache: hcache[k] = code_of(load_dm(hsm))
            hc = hcache[k]
            if hc and hc % 16: wards[hc % 16 - 1] += 1
        if not wards: out.append("%s: no ward among neighbours" % n); continue
        w, votes = wards.most_common(1)[0]
        dist = math.sqrt((near[0][1].x - o.x) ** 2 + (near[0][1].y - o.y) ** 2)
        plan.append((n, sm, dm, code, w))
        out.append("%s: set %d -> ward %d (%d/%d neighbours agree, nearest house %.0f cm)" % (n, code // 16, w, votes, sum(wards.values()), dist))
    out.append("towers to patch: %d" % len(plan))
    todo = plan[:1] if APPLY == 'ONE' else plan
    opts = unreal.GeometryScriptCopyMeshToAssetOptions()
    for p, v in (('enable_recompute_normals', False), ('enable_recompute_tangents', False), ('enable_remove_degenerates', False), ('replace_materials', False)):
        try: opts.set_editor_property(p, v)
        except Exception as e: out.append("opt %s: %s" % (p, str(e)[:80]))
    for n, sm, dm, code, w in todo:
        newx = float(w + 1 + 16 * (code // 16))
        nt = GQ.get_num_triangle_i_ds(dm)
        before_uv0 = tri_uvs(dm, 0, 0)
        changed = 0
        for t in range(nt):
            u = tri_uvs(dm, 5, t)
            if len(u) != 3: continue
            tri = unreal.GeometryScriptUVTriangle()
            tri.set_editor_property('uv0', unreal.Vector2D(newx, u[0].y))
            tri.set_editor_property('uv1', unreal.Vector2D(newx, u[1].y))
            tri.set_editor_property('uv2', unreal.Vector2D(newx, u[2].y))
            GU.set_mesh_triangle_u_vs(dm, 5, t, tri, False)
            changed += 1
        GA.copy_mesh_to_static_mesh(dm, sm, opts, unreal.GeometryScriptMeshWriteLOD())
        chk = load_dm(sm)
        out.append("WROTE %s: %d tris, uv5 code now %s, uv channels %s, uv0 tri0 before %s after %s" % (
            n, changed, code_of(chk), unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_num_uv_channels(sm, 0),
            [(round(x.x, 3), round(x.y, 3)) for x in before_uv0], [(round(x.x, 3), round(x.y, 3)) for x in tri_uvs(chk, 0, 0)]))
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
