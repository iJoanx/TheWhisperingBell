"""Door pairs that wrap onto whatever they are placed against (BP_DoorPair).

Each door of a BP_DoorPair (DoorA, DoorB) gets a picture that is cut out of the surface right
behind it (within WRAP_DEPTH, facing the same way as the door) - walls, towers, sewer pieces,
any mesh - and laid 1.5 cm in front of it, like the tower doors. Move or turn a door and it
re-fits (live, while editing). No surface there: the flat door shows instead.

The picture is a mesh attached to its door (DoorWrap_A / DoorWrap_B on the actor); line traces
hit it on its exact shape, and the pair's E graph treats a hit on it as a hit on its door.

Started with the editor (init_unreal.py); by hand:  py import door_wrap; door_wrap.start()
Re-fit every pair in the level:                       door_wrap.refit_all()
"""
import math
import time
import unreal

BP_CLASS = "BP_DoorPair_C"
WRAP_PREFIX = "DoorWrap_"
WRAP_DEPTH = 100.0          # cm in front of / behind the door that counts as its surface
LIFT = 1.5                  # cm the picture sits off the surface
SKIP_COMPONENTS = ("TowerDoors_", WRAP_PREFIX, "TowerDoorBox_")
_STATE = {"sig": {}, "last": 0.0, "scan": 0.0, "pairs": []}
_TRIS = {}


def gs(name):
    import sewer_builder
    return sewer_builder.gs(name)


def _ws():
    import walls_spline
    return walls_spline


# --------------------------------------------------------------------------- scenery
def _mesh_tris_static(sm):
    """Triangles of a static mesh asset in its own space (cached by asset path)."""
    key = sm.get_path_name()
    if key not in _TRIS:
        m = unreal.DynamicMesh()
        out = []
        try:
            gs("copy_mesh_from_static_mesh")(sm, m, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                             unreal.GeometryScriptMeshReadLOD())
            out = _mesh_tris(m)
        except Exception as e:  # noqa
            unreal.log_warning("Door wrap: %s not read (%s)" % (key, e))
        _TRIS[key] = out
    return _TRIS[key]


def _mesh_tris(m):
    out = []
    for t in range(gs("get_num_triangle_i_ds")(m)):
        r = gs("get_triangle_positions")(m, t)
        vs = [x for x in r if isinstance(x, unreal.Vector)] if isinstance(r, tuple) else []
        ok = [x for x in r if isinstance(x, bool)] if isinstance(r, tuple) else [False]
        if len(vs) == 3 and (not ok or ok[0]):
            out.append(tuple((v.x, v.y, v.z) for v in vs))
    return out


def _bounds_near(origin, extent, centre, reach):
    return all(abs(origin[k] - centre[k]) <= extent[k] + reach for k in range(3))


def _scenery(centre, reach, skip_actor):
    """[(world transform, triangles in local space)] of everything whose bounds come within
    `reach` of `centre` (world): static meshes, instances, generated (dynamic) meshes."""
    out = []
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a == skip_actor or a.is_hidden_ed():
            continue
        try:
            if a.get_class().get_name() == BP_CLASS:
                continue                                  # other door pairs
        except Exception:
            pass
        for c in a.get_components_by_class(unreal.PrimitiveComponent):
            name = c.get_name()
            if name.startswith(SKIP_COMPONENTS) or not c.is_visible():
                continue
            if isinstance(c, unreal.StaticMeshComponent):
                sm = c.get_editor_property("static_mesh")
                if sm is None or sm.get_name() == "SM_DoorPlane":
                    continue
                if isinstance(c, unreal.InstancedStaticMeshComponent):
                    b = sm.get_bounding_box()
                    half = max(b.max.x - b.min.x, b.max.y - b.min.y, b.max.z - b.min.z)
                    for i in range(c.get_instance_count()):
                        xf = c.get_instance_transform(i, True)
                        p = xf.translation
                        r = half * max(abs(xf.scale3d.x), abs(xf.scale3d.y), abs(xf.scale3d.z)) + reach
                        if abs(p.x - centre[0]) <= r and abs(p.y - centre[1]) <= r and abs(p.z - centre[2]) <= r:
                            out.append((xf, _mesh_tris_static(sm)))
                    continue
                o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
                if _bounds_near((o.x, o.y, o.z), (e.x, e.y, e.z), centre, reach):
                    out.append((c.get_world_transform(), _mesh_tris_static(sm)))
            elif isinstance(c, unreal.DynamicMeshComponent):
                o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
                if _bounds_near((o.x, o.y, o.z), (e.x, e.y, e.z), centre, reach):
                    out.append((c.get_world_transform(), _mesh_tris(c.get_dynamic_mesh())))
    return out


# --------------------------------------------------------------------------- fitting
def _patch(door_xf, scenery):
    """Door-space polygons [(poly, uvs)] of the surfaces behind the door, cut to the door."""
    ws = _ws()
    W, H = ws.DOOR_W, ws.DOOR_H
    inv = unreal.MathLibrary.invert_transform(door_xf)
    planes = (((1.0, 0.0, 0.0), -WRAP_DEPTH), ((-1.0, 0.0, 0.0), -WRAP_DEPTH),
              ((0.0, 1.0, 0.0), -W * 0.5), ((0.0, -1.0, 0.0), -W * 0.5),
              ((0.0, 0.0, 1.0), 0.0), ((0.0, 0.0, -1.0), -H))
    polys = []
    for xf, tris in scenery:
        to_door = unreal.MathLibrary.compose_transforms(xf, inv)       # mesh space -> door space
        for tri in tris:
            pts = [unreal.MathLibrary.transform_location(to_door, unreal.Vector(*q)) for q in tri]
            # quick reject: wholly outside the door's box
            if (min(p.x for p in pts) > WRAP_DEPTH or max(p.x for p in pts) < -WRAP_DEPTH or
                    min(p.y for p in pts) > W * 0.5 or max(p.y for p in pts) < -W * 0.5 or
                    min(p.z for p in pts) > H or max(p.z for p in pts) < 0.0):
                continue
            a, b, c = [(p.x, p.y, p.z) for p in pts]
            u = [b[k] - a[k] for k in range(3)]
            v = [c[k] - a[k] for k in range(3)]
            nx = u[1] * v[2] - u[2] * v[1]
            ln = math.sqrt(nx * nx + (u[2] * v[0] - u[0] * v[2]) ** 2 + (u[0] * v[1] - u[1] * v[0]) ** 2)
            # facing out of the door's way (Unreal's winding: this cross product points inwards)
            if ln < 1e-6 or -nx / ln < 0.25:
                continue
            poly = [a, b, c]
            for n, d in planes:
                poly = ws._clip3(poly, n, d)
                if len(poly) < 3:
                    break
            if len(poly) < 3:
                continue
            polys.append(([(q[0] + LIFT, q[1], q[2]) for q in poly],
                          [(0.5 - q[1] / W, 1.0 - q[2] / H) for q in poly]))
    return polys


def _wrap_comp(actor, door, letter):
    """The picture component attached to `door` (made on demand)."""
    name = WRAP_PREFIX + letter
    for c in actor.get_components_by_class(unreal.DynamicMeshComponent):
        if c.get_name() == name:
            return c
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    parent = None
    for h in sds.k2_gather_subobject_data_for_instance(actor):
        o = lib.get_object(lib.get_data(h))
        # Blueprint-made components come back as their templates (DoorA_GEN_VARIABLE)
        if o is not None and (o == door or o.get_name().replace("_GEN_VARIABLE", "") == door.get_name()):
            parent = h
    if parent is None:
        return None
    h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(
        parent_handle=parent, new_class=unreal.DynamicMeshComponent, blueprint_context=None))
    if str(fail):
        unreal.log_warning("Door wrap: could not add %s (%s)" % (name, fail))
        return None
    sds.rename_subobject(h, unreal.Text(name))
    c = lib.get_object(lib.get_data(h))
    c.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
    c.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
    return c


def _set_trace_only(c, on):
    if not on:
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        return
    c.set_collision_profile_name("Custom")
    c.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
    c.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
    c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY, unreal.CollisionResponseType.ECR_BLOCK)
    c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA, unreal.CollisionResponseType.ECR_BLOCK)


def fit(actor):
    ws = _ws()
    mat = unreal.EditorAssetLibrary.load_asset(ws.DOOR_MAT)
    report = []
    for letter in ("A", "B"):
        door = next((c for c in actor.get_components_by_class(unreal.StaticMeshComponent)
                     if c.get_name() == "Door" + letter), None)
        if door is None:
            continue
        xf = door.get_world_transform()
        xf = unreal.Transform(location=xf.translation, rotation=xf.rotation.rotator())   # no scale
        up = unreal.MathLibrary.transform_direction(xf, unreal.Vector(0, 0, ws.DOOR_H * 0.5))
        centre = (xf.translation.x + up.x, xf.translation.y + up.y, xf.translation.z + up.z)
        reach = WRAP_DEPTH + max(ws.DOOR_W, ws.DOOR_H)
        polys = _patch(xf, _scenery(centre, reach, actor))
        wrap = _wrap_comp(actor, door, letter)
        if wrap is None:
            continue
        m = wrap.get_dynamic_mesh()
        m.reset()
        for poly, uvs in polys:
            ids = []
            for q in poly:
                r = gs("add_vertex_to_mesh")(m, unreal.Vector(*q), False)
                ids.append(r[1] if isinstance(r, tuple) else r)
            for k in range(1, len(ids) - 1):
                r = gs("add_triangle_to_mesh")(m, unreal.IntVector(ids[0], ids[k], ids[k + 1]), 0, False)
                tid = r[1] if isinstance(r, tuple) else r
                ws._ensure_uv(m)
                ws._set_uv(m, tid, [uvs[0], uvs[k], uvs[k + 1]])
        wrapped = bool(polys)
        if wrapped:
            try:
                import sewer_builder
                sewer_builder._normals(m)
            except Exception:
                pass
        if mat and wrap.get_material(0) != mat:
            wrap.set_material(0, mat)
        wrap.set_editor_property("cast_shadow", False)
        for prop, val in (("enable_complex_collision", True),
                          ("collision_type", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)):
            try:
                wrap.set_editor_property(prop, val)
            except Exception:
                pass
        _set_trace_only(wrap, wrapped)
        try:
            wrap.notify_mesh_modified()
            wrap.update_collision(False)
        except Exception:
            pass
        # the flat door: only when there is nothing to wrap onto
        door.set_visibility(not wrapped, False)
        _set_trace_only(door, not wrapped)
        report.append("Door%s: %s" % (letter, ("wrapped, %d pieces" % len(polys)) if wrapped else "flat (no surface)"))
    return report


# --------------------------------------------------------------------------- live updates
def _is_pair(a):
    try:
        return a.get_class().get_name() == BP_CLASS
    except Exception:
        return False


def _signature(a):
    out = []
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.get_name() in ("DoorA", "DoorB"):
            t = c.get_world_transform()
            r = t.rotation.rotator()
            out.append((c.get_name(), round(t.translation.x, 1), round(t.translation.y, 1), round(t.translation.z, 1),
                        round(r.yaw, 1), round(r.pitch, 1), round(r.roll, 1)))
    return tuple(sorted(out))


def _tick(dt):
    now = time.time()
    if now - _STATE["last"] < 0.25:
        return
    _STATE["last"] = now
    try:
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if editor.get_game_world():
            return
        # During a map switch the editor briefly has no CurrentWorld. Calling
        # EditorActorSubsystem in that window asserts inside Unreal and crashes
        # the editor (the exception handler below cannot catch that assertion).
        if editor.get_editor_world() is None:
            return
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        if now - _STATE["scan"] > 3.0:
            _STATE["scan"] = now
            _STATE["pairs"] = [a for a in eas.get_all_level_actors() if _is_pair(a)]
            pairs = _STATE["pairs"]
        else:
            pairs = [a for a in eas.get_selected_level_actors() if _is_pair(a)]
        for a in pairs:
            key = a.get_path_name()
            sig = _signature(a)
            if _STATE["sig"].get(key) != sig:
                fit(a)
                _STATE["sig"][key] = sig
    except Exception as e:  # never break the editor tick
        unreal.log_warning("Door wrap: %s" % e)


def start():
    import builtins
    stop()
    builtins._DOOR_WRAP_HANDLE = unreal.register_slate_post_tick_callback(_tick)


def stop():
    import builtins
    h = getattr(builtins, "_DOOR_WRAP_HANDLE", None)
    if h is not None:
        try:
            unreal.unregister_slate_post_tick_callback(h)
        except Exception:
            pass
    builtins._DOOR_WRAP_HANDLE = None


def refit_all():
    _TRIS.clear()
    _STATE["sig"].clear()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    out = []
    for a in eas.get_all_level_actors():
        if _is_pair(a):
            out.append("%s: %s" % (a.get_actor_label(), "; ".join(fit(a))))
            _STATE["sig"][a.get_path_name()] = _signature(a)
    return out
