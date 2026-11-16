import unreal, collections
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump343.txt", "w", encoding="utf-8").write("\n".join(out))
GA, GQ = unreal.GeometryScript_AssetUtils, unreal.GeometryScript_MeshQueries
def code_of(sm):
    dm = unreal.DynamicMesh()
    GA.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    c = collections.Counter()
    n = GQ.get_num_triangle_i_ds(dm)
    for t in range(0, n, max(1, n // 30)):
        u = [x for x in GQ.get_triangle_u_vs(dm, 5, t) if isinstance(x, unreal.Vector2D)]
        if u: c[int(round(u[0].x))] += 1
    return dict(c)
try:
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    cam, rot = ues.get_level_viewport_camera_info()
    out.append("camera %s" % cam)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    rows = []
    for a in eas.get_all_level_actors():
        for c in a.get_components_by_class(unreal.PrimitiveComponent):
            o, e = c.bounds.origin, c.bounds.box_extent
            d = ((o.x - cam.x) ** 2 + (o.y - cam.y) ** 2) ** 0.5
            if d < 8000 and e.z > 600 and abs(e.x - e.y) < 0.35 * max(e.x, e.y):   # tall, round-ish footprint
                rows.append((d, a, c))
    rows.sort(key=lambda r: r[0])
    for d, a, c in rows[:12]:
        sm = c.static_mesh if isinstance(c, unreal.StaticMeshComponent) else None
        mats = [m.get_name() if m else None for m in c.get_materials()] if hasattr(c, 'get_materials') else []
        out.append("%.0f cm  %s [%s] comp %s (%s) mesh %s mats %s code %s nanite %s" % (d, a.get_actor_label(), a.get_class().get_name(), c.get_name(), c.get_class().get_name(),
                   sm.get_name() if sm else None, mats, code_of(sm) if sm else None,
                   sm.get_editor_property('nanite_settings').enabled if sm else None))
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
