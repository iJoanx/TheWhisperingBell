"""Live wall spline (Zippy).

BP_WallSpline (Content/Walls): drop it in a level, edit its spline points (Alt-drag to add points);
the wall rebuilds as you edit. Every spline point gets a tower:
    Tower           : dropdown, the tower mesh for the whole spline (SM_Tower_None = no towers)
    Tower Overrides : optional, one entry per point (by index): a different tower for that point;
                      leave empty to use Tower, SM_Tower_None for no tower there
Between points the wall runs straight and follows the height difference (ramps): the modules
are sheared, so they stay upright instead of leaning. Towers sit at the point height and turn
so they line up with both walls that meet there.

Doors: where a wall meets a tower, the tower gets a door at wall-walk height, in the middle of the
wall: a door picture (T_TowerDoor / M_TowerDoor) cut out of the tower's own surface (it shows on the
tower only, never on anything else), one mesh per door (TowerDoors_N on the wall actor, tag
TowerDoor) that line traces hit on its exact shape. Look at a door and interact (E): you come out of
the same tower's other wall door - through the tower to the next stretch of wall. The Blueprint does
the teleport (UseDoor(Player); in The Whispering Bell, BPI_Interactable's OnInteract calls it), using
the lists DoorBoxes (the door meshes) / DoorTargets this script fills in.

Setup (once):   py import importlib, walls_spline; importlib.reload(walls_spline); walls_spline.make_blueprint()
Live updates:   started by init_unreal.py at editor start  (or walls_spline.start())
"""
import math
import time
import unreal

ROOT = "/Game/Walls"
BP_PATH = ROOT + "/BP_WallSpline"
MESHES = ROOT + "/Meshes"
WALL_MESH = MESHES + "/SM_wall"
MATERIAL = ROOT + "/M_Walls"
DEFAULT_TOWER = MESHES + "/SM_Tower_Square_3"
NO_TOWER = MESHES + "/SM_Tower_None"
# Blender names -> clearer asset names (Blender's Tower_S_* are the round ones, Tower_C_* the square ones)
RENAMES = {"SM_Tower_C_3": "SM_Tower_Square_3", "SM_Tower_C_4": "SM_Tower_Square_4",
           "SM_Tower_S_3": "SM_Tower_Round_3", "SM_Tower_S_4": "SM_Tower_Round_4", "SM_Tower_S_5": "SM_Tower_Round_5",
           "SM_Tower_B_3": "SM_Tower_Big_3"}
SQUARE_TURN_DEG = 45.0     # turns sharper than this: square towers turn 45 deg so both walls hit a face square on
EAL = unreal.EditorAssetLibrary


def gs(name):
    import sewer_builder
    return sewer_builder.gs(name)


# --------------------------------------------------------------------------- blueprint
def _real_type(BEL):
    t = BEL.get_basic_type_by_name("real")
    try:
        t.set_editor_property("pin_sub_category", "double")
    except Exception:
        pass
    return t


def _struct_type(BEL, struct):
    try:
        return BEL.get_struct_type(struct.static_struct())
    except Exception:
        return BEL.get_basic_type_by_name("struct")


def make_blueprint():
    """Creates BP_WallSpline: a spline, a dynamic mesh for the wall, and the per-point settings."""
    BEL = unreal.BlueprintEditorLibrary
    if EAL.does_asset_exist(BP_PATH):
        bp = EAL.load_asset(BP_PATH)
    else:
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", unreal.Actor)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("BP_WallSpline", ROOT, unreal.Blueprint, f)
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        root = sds.k2_gather_subobject_data_for_blueprint(bp)[0]
        for cls, name in ((unreal.SplineComponent, "Spline"), (unreal.DynamicMeshComponent, "WallMesh")):
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=cls, blueprint_context=bp))
            if str(fail):
                raise RuntimeError("could not add %s: %s" % (name, fail))
            sds.rename_subobject(h, unreal.Text(name))
    mesh_t = BEL.get_object_reference_type(unreal.StaticMesh)
    cdo = unreal.get_default_object(bp.generated_class())
    for name, t in (("Tower", mesh_t), ("TowerOverrides", BEL.get_array_type(mesh_t)),
                    ("TowerRotations", BEL.get_array_type(_real_type(BEL))),
                    ("NoWall", BEL.get_array_type(BEL.get_basic_type_by_name("bool"))),
                    ("DoorBoxes", BEL.get_array_type(BEL.get_object_reference_type(unreal.PrimitiveComponent))),
                    ("DoorTargets", BEL.get_array_type(_struct_type(BEL, unreal.Transform)))):
        try:
            cdo.get_editor_property(name)
            continue                                 # already there (avoid Name_0 duplicates)
        except Exception:
            pass
        BEL.add_member_variable(bp, name, t)
        BEL.set_blueprint_variable_instance_editable(bp, name, True)
    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    # doors are used through the project's interact system (BPI_Interactable -> OnInteract -> UseDoor),
    # so the wall does not listen to keys itself
    if EAL.does_asset_exist(DEFAULT_TOWER):
        cdo.set_editor_property("Tower", EAL.load_asset(DEFAULT_TOWER))
    EAL.save_asset(BP_PATH)
    unreal.log("Walls: BP_WallSpline ready")
    return bp


# --------------------------------------------------------------------------- pieces
_SRC = {}
_LEN = {}
_HALF = {}
MAX_SHIFT = 0.9           # square towers move at most this many half-widths off their point
WALL_INSET = 50.0          # cm a wall reaches into a square tower past the face it meets


def _src(path):
    """DynamicMesh copy of a static mesh (cached), or None."""
    if path in _SRC:
        return _SRC[path]
    sm = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    m = None
    if sm:
        m = unreal.DynamicMesh()
        gs("copy_mesh_from_static_mesh")(sm, m, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
        b = sm.get_bounding_box()
        _LEN[path] = max(1.0, b.max.x - b.min.x)
        _HALF[path] = max(1.0, min(b.max.x - b.min.x, b.max.y - b.min.y) * 0.5)   # wall: half its thickness
    _SRC[path] = m
    return m


def rename_meshes():
    """Clearer names for the tower meshes, plus SM_Tower_None (pick it for 'no tower')."""
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for old, new in RENAMES.items():
        if EAL.does_asset_exist(MESHES + "/" + old) and not EAL.does_asset_exist(MESHES + "/" + new):
            EAL.rename_asset(MESHES + "/" + old, MESHES + "/" + new)
    redirs = [a.get_asset() for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(MESHES)
              if str(a.asset_class_path.asset_name) == "ObjectRedirector"]
    if redirs:
        tools.fixup_referencers(redirs)
    if not EAL.does_asset_exist(NO_TOWER):
        m = unreal.DynamicMesh()
        gs("append_box")(m, unreal.GeometryScriptPrimitiveOptions(), unreal.Transform(), 1.0, 1.0, 1.0, 0, 0, 0,
                         unreal.GeometryScriptPrimitiveOriginMode.BASE)
        gs("create_new_static_mesh_asset_from_mesh")(m, NO_TOWER, unreal.GeometryScriptCreateNewStaticMeshAssetOptions())
        EAL.save_asset(NO_TOWER)
    _SRC.clear()


def _path(obj):
    return obj.get_path_name().split(".")[0] if obj else None


# --------------------------------------------------------------------------- build
def _prop(actor, name, default):
    try:
        v = actor.get_editor_property(name)
        return v if v is not None else default
    except Exception:
        return default


def _settings(actor, n):
    """Tower mesh path (or None) for every spline point."""
    tower = _path(_prop(actor, "Tower", None))
    over = list(_prop(actor, "TowerOverrides", []) or [])
    if len(over) < n:                            # one entry per point, so they show up in Details
        over += [None] * (n - len(over))
        try:
            actor.set_editor_property("TowerOverrides", over)
        except Exception:
            pass
    out = []
    for o in over[:n]:
        p = _path(o) or tower
        out.append(None if p == NO_TOWER else p)
    return out


def _mark_edited(spline):
    """Points set from Python must survive the blueprint's construction script (like hand edits)."""
    for prop in ("spline_has_been_edited", "b_spline_has_been_edited"):
        try:
            spline.set_editor_property(prop, True)
            return
        except Exception:
            pass


def _yaw(d):
    return math.degrees(math.atan2(d[1], d[0]))


def _points(spline):
    n = spline.get_number_of_spline_points()
    pts, changed = [], False
    for i in range(n):
        p = spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.LOCAL)
        pts.append((p.x, p.y, p.z))
        if spline.get_spline_point_type(i) != unreal.SplinePointType.LINEAR:   # walls run straight
            spline.set_spline_point_type(i, unreal.SplinePointType.LINEAR, False)
            changed = True
    if changed:
        spline.update_spline()
    return pts


SQUARE_KEYS = ("Square", "Beacon")     # towers with flat faces (walls meet the face centres)


def _is_square(path):
    return bool(path) and any(k in path for k in SQUARE_KEYS)


def _tower_yaw(pts, i, closed, path):
    n = len(pts)
    dirs = []
    if closed or i > 0:
        a = pts[i - 1]
        dirs.append((pts[i][0] - a[0], pts[i][1] - a[1]))
    if closed or i < n - 1:
        b = pts[(i + 1) % n]
        dirs.append((b[0] - pts[i][0], b[1] - pts[i][1]))
    us = []
    for d in dirs:
        L = math.hypot(*d)
        if L > 1e-3:
            us.append((d[0] / L, d[1] / L))
    if not us:
        return 0.0
    if len(us) == 1:
        return _yaw(us[0])
    s = (us[0][0] + us[1][0], us[0][1] + us[1][1])
    yaw = _yaw(s) if math.hypot(*s) > 1e-3 else _yaw(us[0]) + 90.0     # bisector of the two walls
    if _is_square(path):
        # turns up to 45 deg: sides along the bisector; sharper: a corner of the square points
        # between the walls, so each wall runs into its own face (square on at 90 deg)
        turn = abs((_yaw(us[1]) - _yaw(us[0]) + 180.0) % 360.0 - 180.0)
        if turn > SQUARE_TURN_DEG:
            yaw += 45.0
    return yaw


def _neighbours(pts, i, closed):
    """[(neighbour index, unit direction from point i towards it)]"""
    n = len(pts)
    out = []
    for j in ((i - 1) if (closed or i > 0) else None, (i + 1) % n if (closed or i < n - 1) else None):
        if j is None or j == i:
            continue
        d = (pts[j][0] - pts[i][0], pts[j][1] - pts[i][1])
        L = math.hypot(*d)
        if L > 1e-3:
            out.append((j, (d[0] / L, d[1] / L)))
    return out


def _square_fit(pts, i, closed, yaw, half):
    """Square tower at point i: shift the tower so each wall meets the MIDDLE of the face it runs
    into, and say how far along each wall that face is. Returns ((dx, dy), {neighbour: t})."""
    nb = _neighbours(pts, i, closed)
    P = pts[i]
    faces = [(math.cos(math.radians(yaw + 90 * k)), math.sin(math.radians(yaw + 90 * k))) for k in range(4)]
    hit = []
    for j, w in nb:
        k = max(range(4), key=lambda k: faces[k][0] * w[0] + faces[k][1] * w[1])
        hit.append((j, w, faces[k]))
    T = (P[0], P[1])
    if len(hit) == 2 and hit[0][2] != hit[1][2]:
        # face centre T + half*n must lie on the wall line through P:  cross(T - (P - half*n), w) = 0
        rows = []
        for j, w, nrm in hit:
            q = (P[0] - half * nrm[0], P[1] - half * nrm[1])
            rows.append((w[1], -w[0], q[0] * w[1] - q[1] * w[0]))
        (a1, b1, c1), (a2, b2, c2) = rows
        det = a1 * b2 - a2 * b1
        if abs(det) > 1e-3:
            tx, ty = (c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det
            d = math.hypot(tx - P[0], ty - P[1])
            if d > MAX_SHIFT * half:
                # very sharp corners would need the tower far off the corner: move it as far as
                # allowed towards the walls (the corner point stays inside the tower)
                k = MAX_SHIFT * half / d
                tx, ty = P[0] + (tx - P[0]) * k, P[1] + (ty - P[1]) * k
            T = (tx, ty)
    reach = {}
    hw = _HALF.get(WALL_MESH, 230.0)
    u = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
    v = (-u[1], u[0])
    for j, w, nrm in hit:
        # where each side edge of the wall leaves the tower's square (measured from P along the
        # wall; it may leave through a neighbouring face near a corner): the wall must reach
        # back to the nearer of the two, or the other side leaves a gap
        ts = []
        for side in (-hw, hw):
            sx, sy = P[0] - w[1] * side - T[0], P[1] + w[0] * side - T[1]
            lo, hi = -1e9, 1e9
            for ax in (u, v):
                p0 = sx * ax[0] + sy * ax[1]
                d = w[0] * ax[0] + w[1] * ax[1]
                if abs(d) < 1e-6:
                    if abs(p0) > half:
                        lo, hi = 1.0, 0.0          # runs beside the square, never inside
                    continue
                t1, t2 = (-half - p0) / d, (half - p0) / d
                lo, hi = max(lo, min(t1, t2)), min(hi, max(t1, t2))
            if hi >= lo:
                ts.append(hi)                      # may be behind P: the wall then starts back there
        # (negative reach = the wall continues past the spline point into the shifted tower)
        reach[j] = (min(ts) - WALL_INSET) if ts else 0.0
    return (T[0] - P[0], T[1] - P[1]), reach


MITRE_MAX = 4.0          # corners without a tower: a wall reaches at most this many half-widths past
                         # the point to fill the outside of the corner (very sharp turns)


JOIN_TOL = 60.0          # cm: an open end of one wall spline on an open end of another = one corner


def _joins(actor, pts, closed):
    """Open ends of this wall that sit on an open end of ANOTHER wall spline: {end index: ((x, y)
    unit direction, in this actor's local space, from the end along the other wall), other}."""
    out = {}
    if closed or len(pts) < 2:
        return out
    xf = actor.get_actor_transform()
    me = actor.get_path_name()
    others = [a for a in (_STATE.get("actors") or []) if a.get_path_name() != me]
    if not others:
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        others = [a for a in eas.get_all_level_actors() if _is_wall(a) and a.get_path_name() != me]
    W = unreal.SplineCoordinateSpace.WORLD
    for e in (0, len(pts) - 1):
        pw = unreal.MathLibrary.transform_location(xf, unreal.Vector(*pts[e]))
        for o in others:
            try:
                sp = o.get_component_by_class(unreal.SplineComponent)
                m = sp.get_number_of_spline_points() if sp else 0
                if m < 2 or sp.is_closed_loop():
                    continue
                for oe, onb in ((0, 1), (m - 1, m - 2)):
                    q = sp.get_location_at_spline_point(oe, W)
                    if math.hypot(q.x - pw.x, q.y - pw.y) > JOIN_TOL or abs(q.z - pw.z) > 300.0:
                        continue
                    r = sp.get_location_at_spline_point(onb, W)
                    dl = unreal.MathLibrary.inverse_transform_direction(xf, unreal.Vector(r.x - q.x, r.y - q.y, 0.0))
                    L = math.hypot(dl.x, dl.y)
                    if L > 1e-3:
                        out[e] = ((dl.x / L, dl.y / L), o)
                        raise StopIteration
            except StopIteration:
                break
            except Exception:
                continue
    return out


def _mitre(pts, i, far, closed, skips, towers, fits, joins=None):
    """Corner at point i (no tower there, a wall on both sides): the plane the wall towards `far`
    is cut at - the line halving the corner - as (normal of the side to cut away, how far the
    wall must run on past the point to fill the corner's outside). None: no mitre at this end."""
    n = len(pts)
    if towers[i] is not None or i in fits:
        return None
    other = None
    for j, w in _neighbours(pts, i, closed):
        if j != far:
            other = (j, w)
    if other is not None:
        # the wall to that other neighbour must exist (not a NoWall gap)
        seg_other = i if other[0] == (i + 1) % n else (i - 1) % n
        if seg_other < len(skips) and skips[seg_other]:
            return None
    elif joins and i in joins:
        other = (None, joins[i][0])              # the wall of another spline that ends here
    else:
        return None
    d0 = (pts[far][0] - pts[i][0], pts[far][1] - pts[i][1])
    L0 = math.hypot(*d0)
    if L0 < 1e-3:
        return None
    w0 = (d0[0] / L0, d0[1] / L0)
    w1 = other[1]
    m = (w0[0] - w1[0], w0[1] - w1[1])          # points into this wall's side of the corner
    lm = math.hypot(*m)
    if lm < 1e-6:
        return None                             # folds straight back on itself
    m = (m[0] / lm, m[1] / lm)
    cosa = max(-1.0, min(1.0, w0[0] * w1[0] + w0[1] * w1[1]))
    half_angle = math.acos(cosa) * 0.5          # half the angle between the two walls
    hw = _HALF.get(WALL_MESH, 230.0) * 1.3 + 20.0
    ext = 0.0 if cosa < -0.999 else min(hw * MITRE_MAX, hw / max(1e-3, math.tan(half_angle)))
    return ((-m[0], -m[1]), ext)


def _mitre_x(px, py, ax, n):
    """x where the line along the wall through (., py) meets the mitre plane through (ax, 0) with
    horizontal normal n (wall-local frame: x along the wall)."""
    return ax - py * n[1] / n[0]


def _project_to_mitres(seg, cuts):
    """Wall-local mesh: slide every vertex lying beyond a mitre plane back along the wall onto it,
    so the run ends exactly on the corner's halving line (nothing deleted, no plane cut). UVs of
    the triangles touched are re-evaluated at the new positions from each triangle's original
    mapping, so the texture isn't squashed. cuts: [((ax, 0), n)] with n pointing to the side
    that goes (wall-local, n[0] != 0)."""
    cuts = [(ax, n) for (ax, n) in cuts if abs(n[0]) > 1e-6]
    if not cuts:
        return
    moved = {}
    nv = gs("get_num_vertex_i_ds")(seg)
    for vid in range(nv):
        r = gs("get_vertex_position")(seg, vid)
        if isinstance(r, tuple):
            q, valid = r[0], (r[1] if len(r) > 1 else True)
        else:
            q, valid = r, True
        if not valid or not isinstance(q, unreal.Vector):
            continue
        x = q.x
        for ax, n in cuts:
            if (x - ax) * n[0] + q.y * n[1] > 0.0:
                x = _mitre_x(x, q.y, ax, n)
        if abs(x - q.x) > 1e-4:
            moved[vid] = (q, unreal.Vector(x, q.y, q.z))
    if not moved:
        return
    # texture: the triangles with a moved corner keep their original mapping
    nsets = 1
    try:
        nsets = max(1, gs("get_num_uv_sets")(seg))
    except Exception:
        pass
    fix = []
    for t in range(gs("get_num_triangle_i_ds")(seg)):
        try:
            tri = gs("get_triangle_indices")(seg, t)
        except Exception:
            break
        ids = None
        if isinstance(tri, tuple):
            for x_ in tri:
                if hasattr(x_, "x") and hasattr(x_, "z") and not isinstance(x_, unreal.Vector):
                    ids = (x_.x, x_.y, x_.z)
            valid = tri[-1] if isinstance(tri[-1], bool) else True
        else:
            ids, valid = (tri.x, tri.y, tri.z), True
        if not valid or ids is None or not any(i in moved for i in ids):
            continue
        old = []
        for i in ids:
            if i in moved:
                old.append(moved[i][0])
            else:
                r = gs("get_vertex_position")(seg, i)
                old.append(r[0] if isinstance(r, tuple) else r)
        uvs = []
        for k in range(nsets):
            try:
                u = gs("get_triangle_u_vs")(seg, k, t)
                u = [x_ for x_ in u if isinstance(x_, unreal.Vector2D)] if isinstance(u, tuple) else []
            except Exception:
                u = []
            uvs.append(u if len(u) == 3 else None)
        fix.append((t, ids, old, uvs))
    for vid, (q, new) in moved.items():
        gs("set_vertex_position")(seg, vid, new, True)

    def bary(p, A, B, C):
        """barycentric coords of p projected onto the plane of triangle ABC (extrapolates)."""
        v0 = (B.x - A.x, B.y - A.y, B.z - A.z)
        v1 = (C.x - A.x, C.y - A.y, C.z - A.z)
        v2 = (p.x - A.x, p.y - A.y, p.z - A.z)
        d00 = sum(a_ * a_ for a_ in v0)
        d01 = sum(a_ * b_ for a_, b_ in zip(v0, v1))
        d11 = sum(a_ * a_ for a_ in v1)
        d20 = sum(a_ * b_ for a_, b_ in zip(v2, v0))
        d21 = sum(a_ * b_ for a_, b_ in zip(v2, v1))
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-9:
            return None
        v = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        return (1.0 - v - w, v, w)
    for t, ids, old, uvs in fix:
        news = [moved[i][1] if i in moved else old[j] for j, i in enumerate(ids)]
        for k, uv in enumerate(uvs):
            if uv is None:
                continue
            out = []
            for p in news:
                bc = bary(p, *old)
                if bc is None:
                    out = None
                    break
                out.append(unreal.Vector2D(bc[0] * uv[0].x + bc[1] * uv[1].x + bc[2] * uv[2].x,
                                           bc[0] * uv[0].y + bc[1] * uv[1].y + bc[2] * uv[2].y))
            if out is None:
                continue
            tri = unreal.GeometryScriptUVTriangle()
            tri.set_editor_property("uv0", out[0])
            tri.set_editor_property("uv1", out[1])
            tri.set_editor_property("uv2", out[2])
            try:
                gs("set_mesh_triangle_u_vs")(seg, k, t, tri, True)
            except Exception:
                pass


def _wall_segment(dst, wall, mod, a, b, m0=None, m1=None):
    """Wall modules from a to b (local space): fitted to the run length, sheared to the height
    change so they stay upright on ramps. m0 / m1: mitre at the a / b end ((normal, extension),
    see _mitre) - the wall runs on past the point and is cut along the corner's halving line."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    L = math.hypot(dx, dy)
    if L < 1.0:
        return
    e0 = m0[1] if m0 else 0.0
    e1 = m1[1] if m1 else 0.0
    slope = dz / L
    u = (dx / L, dy / L)
    a2 = (a[0] - u[0] * e0, a[1] - u[1] * e0, a[2] - slope * e0)
    L2 = L + e0 + e1
    count = max(1, int(round(L2 / mod)))
    sx = L2 / (count * mod)
    seg = unreal.DynamicMesh()
    for k in range(count):
        xf = unreal.Transform(location=unreal.Vector((k + 0.5) * L2 / count, 0, 0), scale=unreal.Vector(sx, 1, 1))
        gs("append_mesh")(seg, wall, xf)
    if m0 or m1:
        # mitres, in the wall's own frame (x along the wall from a2, y across): the corner point a
        # is at x = e0, b at x = e0 + L
        v = (-u[1], u[0])
        cuts = []
        if m0:
            cuts.append((e0, (m0[0][0] * u[0] + m0[0][1] * u[1], m0[0][0] * v[0] + m0[0][1] * v[1])))
        if m1:
            cuts.append((e0 + L, (m1[0][0] * u[0] + m1[0][1] * u[1], m1[0][0] * v[0] + m1[0][1] * v[1])))
        _project_to_mitres(seg, cuts)
    for vid in range(gs("get_num_vertex_i_ds")(seg)):
        r = gs("get_vertex_position")(seg, vid)
        q = r[0] if isinstance(r, tuple) else r
        if isinstance(r, tuple) and len(r) > 1 and r[1] is False:
            continue
        if isinstance(q, unreal.Vector):
            gs("set_vertex_position")(seg, vid, unreal.Vector(q.x, q.y, q.z + q.x * slope), True)
    xf = unreal.Transform(location=unreal.Vector(*a2), rotation=unreal.Rotator(roll=0, pitch=0, yaw=_yaw((dx, dy))))
    gs("append_mesh")(dst, seg, xf)


CHUNK_LENGTH = 4000.0    # cm of wall per mesh chunk (each chunk is culled on its own)


def _plan(pts, closed):
    """Wall segments and towers grouped into chunks of about CHUNK_LENGTH."""
    n = len(pts)
    segs = n if closed else n - 1
    seg_chunk, c, acc = [], 0, 0.0
    for i in range(max(segs, 0)):
        a, b = pts[i], pts[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if acc > 0.0 and acc + L * 0.5 > CHUNK_LENGTH:
            c += 1
            acc = 0.0
        seg_chunk.append(c)
        acc += L
    tower_chunk = [seg_chunk[min(i, len(seg_chunk) - 1)] if seg_chunk else 0 for i in range(n)]
    return segs, seg_chunk, tower_chunk, (max(seg_chunk) + 1 if seg_chunk else 1)


def _instance_comps(actor, cls, prefix, count):
    """`prefix`0.. instance components of `cls` on the actor, at least `count` of them (sorted).
    Instance components survive the blueprint's construction script; its own components don't."""
    def find():
        comps = [c for c in actor.get_components_by_class(cls) if c.get_name().startswith(prefix)]
        tail = lambda c: c.get_name()[len(prefix):]
        return sorted(comps, key=lambda c: int(tail(c)) if tail(c).isdigit() else 0)
    comps = find()
    if len(comps) < count:
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        for k in range(len(comps), count):
            root = sds.k2_gather_subobject_data_for_instance(actor)[0]
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(
                parent_handle=root, new_class=cls, blueprint_context=None))
            if str(fail):
                unreal.log_warning("Walls: could not add %s (%s)" % (prefix, fail))
                break
            used = {c.get_name() for c in actor.get_components_by_class(unreal.ActorComponent)}
            j = k
            while "%s%d" % (prefix, j) in used:
                j += 1
            sds.rename_subobject(h, unreal.Text("%s%d" % (prefix, j)))
        comps = find()
    return comps


def _col_path(path):
    """Collision counterpart of a piece (plain-mesh copy of its UCX parts), if imported."""
    return ROOT + "/Collision/" + path.split("/")[-1] + "_COL" if path else None


def _col_src(path):
    return _src(_col_path(path)) or _src(path)


def _chunks(actor, count):
    return _instance_comps(actor, unreal.DynamicMeshComponent, "WallChunk_", count)


TOWER_ISM_PREFIX = "TowerISM_"


def _place_towers(actor, per_mesh):
    """{mesh path: [transforms]} -> one instanced component per mesh (made on demand, emptied
    when a mesh is no longer used)."""
    comps = {c.get_name(): c for c in actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent)
             if c.get_name().startswith(TOWER_ISM_PREFIX)}
    wanted = {TOWER_ISM_PREFIX + p.split("/")[-1]: p for p in per_mesh}
    missing = [n for n in wanted if n not in comps]
    if missing:
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        for name in missing:
            root = sds.k2_gather_subobject_data_for_instance(actor)[0]
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(
                parent_handle=root, new_class=unreal.HierarchicalInstancedStaticMeshComponent, blueprint_context=None))
            if str(fail):
                unreal.log_warning("Walls: could not add %s (%s)" % (name, fail))
                continue
            sds.rename_subobject(h, unreal.Text(name))
        comps = {c.get_name(): c for c in actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent)
                 if c.get_name().startswith(TOWER_ISM_PREFIX)}
    for name, c in comps.items():
        c.clear_instances()
        path = wanted.get(name)
        if not path:
            continue
        sm = EAL.load_asset(path)
        if c.get_editor_property("static_mesh") != sm:
            c.set_static_mesh(sm)
        c.add_instances(per_mesh[path], False, False)
        # instanced bodies only pick up the mesh's collision when collision is switched on afresh
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_collision_profile_name("BlockAll")
        c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)


def _remove_tower_comps(actor):
    """Clean-up of the short-lived 'click the tower' version: its Tower_N components."""
    comps = [c for c in actor.get_components_by_class(unreal.StaticMeshComponent) if c.get_name().startswith("Tower_")]
    if not comps:
        return
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_instance(actor)
    root = handles[0]
    for h in handles:
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
        if obj in comps:
            try:
                sds.delete_subobject(root, h, None)
            except Exception:
                obj.set_static_mesh(None)


def _finish_chunk(comp, mat):
    try:
        if comp.get_editor_property("draw_path") != unreal.DynamicMeshDrawPath.STATIC_DRAW:
            comp.set_editor_property("draw_path", unreal.DynamicMeshDrawPath.STATIC_DRAW)   # cheaper than per-frame
    except Exception:
        pass
    if mat and comp.get_material(0) != mat:
        comp.set_material(0, mat)
    for prop, val in (("enable_complex_collision", True),
                      ("collision_type", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)):
        try:
            comp.set_editor_property(prop, val)
        except Exception:
            pass
    try:
        comp.notify_mesh_modified()
        comp.update_collision(False)
    except Exception:
        pass


def _set_simple(comp, col_mesh):
    """Simple collision of a chunk = one convex hull per separate part of col_mesh."""
    o = unreal.GeometryScriptCollisionFromMeshOptions()
    o.set_editor_property("method", unreal.GeometryScriptCollisionGenerationMethod.CONVEX_HULLS)
    o.set_editor_property("max_convex_hulls_per_mesh", 1)
    o.set_editor_property("simplify_hulls", False)
    o.set_editor_property("auto_detect_boxes", False)
    shapes = []
    if gs("get_num_triangle_i_ds")(col_mesh) > 0:
        r = gs("split_mesh_by_components")(col_mesh, unreal.DynamicMeshPool())
        for p in (r[1] if isinstance(r, tuple) else r):
            c = gs("generate_collision_from_mesh")(p, o)
            shapes.append(c[0] if isinstance(c, tuple) else c)
    total = gs("combine_simple_collision_array")(shapes) if shapes else unreal.GeometryScriptSimpleCollision()
    total = total[0] if isinstance(total, tuple) else total
    gs("set_simple_collision_of_dynamic_mesh_component")(total, comp, unreal.GeometryScriptSetSimpleCollisionOptions())


def _remove_comps(actor, cls, prefix):
    comps = [c for c in actor.get_components_by_class(cls) if c.get_name().startswith(prefix)]
    if not comps:
        return
    # emptied, not deleted: deleting instance components from Python can crash the editor
    for c in comps:
        if gs("get_num_triangle_i_ds")(c.get_dynamic_mesh()) > 0:
            c.get_dynamic_mesh().reset()
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_visibility(False, False)


def _remap(old_pos, old_over, pts):
    """Per-point overrides follow their points when points are added or removed."""
    if not old_pos or len(old_pos) == len(pts):
        return (list(old_over) + [None] * len(pts))[:len(pts)]
    out = []
    for p in pts:
        best = None
        for i, q in enumerate(old_pos):
            d = math.dist(p, q)
            if d < 1.0 and (best is None or d < best[0]):
                best = (d, i)
        out.append(old_over[best[1]] if best and best[1] < len(old_over) else None)
    return out


def rebuild(actor):
    spline = actor.get_component_by_class(unreal.SplineComponent)
    if not spline:
        return
    key = actor.get_path_name()
    pts = _points(spline)
    if len(pts) == 2 and abs(pts[1][0] - pts[0][0] - 100.0) < 0.01 and abs(pts[1][1] - pts[0][1]) < 0.01:
        # brand-new actor: start with a usable length
        _mark_edited(spline)
        spline.set_location_at_spline_point(1, unreal.Vector(pts[0][0] + 3000.0, pts[0][1], pts[0][2]),
                                            unreal.SplineCoordinateSpace.LOCAL, True)
        pts = _points(spline)
    old_pos = _STATE["pos"].get(key)
    over = list(_prop(actor, "TowerOverrides", []) or [])
    over += [None] * (max(len(old_pos or []), len(pts)) - len(over))
    new_over = _remap(old_pos, over, pts)
    if [_path(o) for o in new_over] != [_path(o) for o in (_prop(actor, "TowerOverrides", []) or [])]:
        actor.set_editor_property("TowerOverrides", new_over)   # re-runs the construction script
        spline = actor.get_component_by_class(unreal.SplineComponent)
    # extra yaw per point (degrees, on top of the automatic direction); follows its point too
    rots = [float(r or 0.0) for r in (_prop(actor, "TowerRotations", []) or [])]
    rots += [0.0] * (max(len(old_pos or []), len(pts)) - len(rots))
    new_rots = [float(r or 0.0) for r in _remap(old_pos, rots, pts)]
    if [round(r, 3) for r in new_rots] != [round(float(r), 3) for r in (_prop(actor, "TowerRotations", []) or [])]:
        try:
            actor.set_editor_property("TowerRotations", new_rots)
        except Exception:
            pass
        spline = actor.get_component_by_class(unreal.SplineComponent)
    closed = spline.is_closed_loop()
    tower = _path(_prop(actor, "Tower", None))
    towers = []
    for o in new_over:
        p = _path(o) or tower
        towers.append(None if p == NO_TOWER else p)
    yaws = [_tower_yaw(pts, i, closed, towers[i]) + new_rots[i] for i in range(len(pts))]
    # NoWall[i] ticked: no wall between point i and point i+1
    sk = [bool(x) for x in (_prop(actor, "NoWall", []) or [])]
    sk += [False] * (max(len(old_pos or []), len(pts)) - len(sk))
    skips = [bool(x) for x in _remap(old_pos, sk, pts)]
    if skips != [bool(x) for x in (_prop(actor, "NoWall", []) or [])]:
        try:
            actor.set_editor_property("NoWall", skips)
        except Exception:
            pass
    # square towers: where they sit and how far the walls go into them
    fits = {}
    for i in range(len(pts)):
        path = towers[i]
        if _is_square(path) and _src(path):
            fits[i] = _square_fit(pts, i, closed, yaws[i], _HALF[path])
    # wall splines that end where this one ends: their walls meet ours in a mitred corner
    joins = _joins(actor, pts, closed)
    _STATE.setdefault("joins", {})[key] = [o for (_, o) in joins.values()]
    # walls, in chunks
    segs, seg_chunk, tower_chunk, count = _plan(pts, closed)
    comps = _chunks(actor, count)
    meshes = [c.get_dynamic_mesh() for c in comps]
    # simple collision: the UCX parts (solid wall, thick parapet) laid out like the wall, one
    # convex hull per part; complex collision: the wall mesh itself (project default)
    cmeshes = [unreal.DynamicMesh() for _ in comps]
    for dm in meshes:
        dm.reset()                                   # unused chunks stay empty
    wall = _src(WALL_MESH)
    wall_col = _col_src(WALL_MESH)
    if wall and meshes:
        for i in range(segs):
            if skips[i]:
                continue                             # no wall from point i to the next
            j = (i + 1) % len(pts)
            a, b = pts[i], pts[j]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            t0 = fits[i][1].get(j, 0.0) if i in fits else 0.0      # stop at the square tower's face
            t1 = fits[j][1].get(i, 0.0) if j in fits else 0.0
            if L > 1.0 and t0 + t1 < L - 10.0:
                lerp = lambda t: tuple(a[k] + (b[k] - a[k]) * t / L for k in range(3))
                a, b = lerp(t0), lerp(L - t1)
            # corners with no tower: the two walls meet on the line halving the corner
            m0 = _mitre(pts, i, j, closed, skips, towers, fits, joins) if t0 == 0.0 else None
            m1 = _mitre(pts, j, i, closed, skips, towers, fits, joins) if t1 == 0.0 else None
            dm = meshes[min(seg_chunk[i], len(meshes) - 1)]
            _wall_segment(dm, wall, _LEN[WALL_MESH], a, b, m0, m1)
            if cmeshes and wall_col:
                _wall_segment(cmeshes[min(seg_chunk[i], len(cmeshes) - 1)], wall_col, _LEN[WALL_MESH], a, b, m0, m1)
    mat = EAL.load_asset(MATERIAL)
    base = next((c for c in actor.get_components_by_class(unreal.DynamicMeshComponent)
                 if not c.get_name().startswith(("WallChunk_", DOOR_COMP_PREFIX, "WallCol_"))), None)
    if base:
        base.get_dynamic_mesh().reset()
    # towers: one instanced component per tower mesh (instances use the mesh's own simple collision)
    per_mesh = {}
    doors = []
    n_pts = len(pts)
    for i, p in enumerate(pts):
        path = towers[i]
        if path and EAL.does_asset_exist(path):
            off = fits[i][0] if i in fits else (0.0, 0.0)
            xf = unreal.Transform(location=unreal.Vector(p[0] + off[0], p[1] + off[1], p[2]),
                                  rotation=unreal.Rotator(roll=0, pitch=0, yaw=yaws[i]))
            per_mesh.setdefault(path, []).append(xf)
            # a door where each of this spline's walls meets the tower, at wall-walk level
            for j, seg in (((i - 1) % n_pts, (i - 1) % n_pts), ((i + 1) % n_pts, i)):
                if not closed and (j < 0 or j >= n_pts or (j == n_pts - 1 and i == 0) or (j == 0 and i == n_pts - 1)):
                    continue
                if j == i or seg >= segs or skips[seg]:
                    continue
                q = pts[j]
                L = math.hypot(q[0] - p[0], q[1] - p[1])
                if L > 1.0:
                    doors.append((path, xf, yaws[i], p, ((q[0] - p[0]) / L, (q[1] - p[1]) / L), i,
                                  (q[2] - p[2]) / L))
    _place_towers(actor, per_mesh)
    try:
        _place_doors(actor, doors)
    except Exception as e:  # noqa
        unreal.log_warning("Walls: doors not placed (%s)" % e)
    for c, cm in zip(comps, cmeshes):
        _finish_chunk(c, mat)
        _set_simple(c, cm)
        c.set_collision_profile_name("BlockAll")
        c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    _remove_comps(actor, unreal.DynamicMeshComponent, "WallCol_")   # old separate collision chunks
    _remove_tower_comps(actor)
    _STATE["pos"][key] = list(pts)


# --------------------------------------------------------------------------- tower doors
# Doors: see the top of this file. One per wall meeting a tower, on the tower, at wall-walk height.
DOOR_W = 218.0            # cm (the door picture is 32 x 50 pixels: width / height = 0.64)
DOOR_H = 340.0
DOOR_LIFT = 1.5           # cm the picture sits off the tower surface (no flicker)
DOOR_TEX = ROOT + "/T_TowerDoor"
DOOR_MAT = ROOT + "/M_TowerDoor"
DOOR_COMP_PREFIX = "TowerDoors_"
_TRIS = {}


def make_door_assets(png=None):
    """Imports the door picture (Content/Python/import/walls/T_TowerDoor.png) and makes M_TowerDoor
    (unlit, cut out by the picture's alpha).
        py import walls_spline; walls_spline.make_door_assets()"""
    import os
    png = png or os.path.join(os.path.dirname(os.path.abspath(__file__)), "import", "walls", "T_TowerDoor.png")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", png)
    task.set_editor_property("destination_path", ROOT)
    task.set_editor_property("destination_name", DOOR_TEX.split("/")[-1])
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = EAL.load_asset(DOOR_TEX)
    for prop, val in (("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON),
                      ("filter", unreal.TextureFilter.TF_NEAREST),             # crisp pixels, like the walls
                      ("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS),
                      ("address_x", unreal.TextureAddress.TA_CLAMP), ("address_y", unreal.TextureAddress.TA_CLAMP)):
        try:
            tex.set_editor_property(prop, val)
        except Exception as e:  # noqa
            unreal.log_warning("Walls: door texture %s not set (%s)" % (prop, e))
    EAL.save_asset(DOOR_TEX)
    MEL = unreal.MaterialEditingLibrary
    if EAL.does_asset_exist(DOOR_MAT):
        mat = EAL.load_asset(DOOR_MAT)
        MEL.delete_all_material_expressions(mat)
    else:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            DOOR_MAT.split("/")[-1], ROOT, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)   # like M_Walls
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("opacity_mask_clip_value", 0.5)
    t = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -400, 0)
    t.set_editor_property("parameter_name", "Door")
    t.set_editor_property("texture", tex)
    MEL.connect_material_property(t, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(t, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(t, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    MEL.recompile_material(mat)
    EAL.save_asset(DOOR_MAT)
    return mat


def _tower_tris(path):
    """The tower's triangles in its own space [(p0, p1, p2)], cached."""
    if path not in _TRIS:
        m = _src(path)
        out = []
        if m:
            for t in range(gs("get_num_triangle_i_ds")(m)):
                r = gs("get_triangle_positions")(m, t)
                vs = [x for x in r if isinstance(x, unreal.Vector)] if isinstance(r, tuple) else []
                ok = [x for x in r if isinstance(x, bool)] if isinstance(r, tuple) else [False]
                if len(vs) == 3 and (not ok or ok[0]):
                    out.append(tuple((v.x, v.y, v.z) for v in vs))
        _TRIS[path] = out
    return _TRIS[path]


def _clip3(poly, n, d):
    """Part of a 3D polygon where n.p >= d."""
    out = []
    k = len(poly)
    for i in range(k):
        a, b = poly[i], poly[(i + 1) % k]
        fa = n[0] * a[0] + n[1] * a[1] + n[2] * a[2] - d
        fb = n[0] * b[0] + n[1] * b[1] + n[2] * b[2] - d
        if fa >= 0:
            out.append(a)
        if (fa >= 0) != (fb >= 0):
            t = fa / (fa - fb)
            out.append(tuple(a[j] + (b[j] - a[j]) * t for j in range(3)))
    return out


def _door_patch(path, dl, c0, z0):
    """The door rectangle cut out of the tower's outside where a wall meets it: centred on the
    wall's middle line (through c0, tower space, running out along dl), from height z0 (the
    wall walk) up DOOR_H. Returns [(polygon, uvs)] and how far out along dl the surface is."""
    el = (-dl[1], dl[0], 0.0)
    d3 = (dl[0], dl[1], 0.0)
    cd = c0[0] * dl[0] + c0[1] * dl[1]
    ce = c0[0] * el[0] + c0[1] * el[1]
    polys, front = [], None
    for tri in _tower_tris(path):
        a, b, c = tri
        u = [b[j] - a[j] for j in range(3)]
        v = [c[j] - a[j] for j in range(3)]
        nrm = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = math.sqrt(sum(x * x for x in nrm))
        # only faces looking out along the wall (either winding: Unreal's triangles turn the
        # other way round than Blender's, so the sign of the cross product says nothing)
        if ln < 1e-6 or abs(nrm[0] * d3[0] + nrm[1] * d3[1]) / ln < 0.25:
            continue
        poly = [a, b, c]
        for n, dd in ((d3, cd), (el, ce - DOOR_W * 0.5), ((-el[0], -el[1], 0.0), -ce - DOOR_W * 0.5),
                      ((0.0, 0.0, 1.0), z0), ((0.0, 0.0, -1.0), -z0 - DOOR_H)):
            poly = _clip3(poly, n, dd)
            if len(poly) < 3:
                break
        if len(poly) < 3:
            continue
        lifted = [(q[0] + dl[0] * DOOR_LIFT, q[1] + dl[1] * DOOR_LIFT, q[2]) for q in poly]
        uvs = [((q[0] * el[0] + q[1] * el[1] - ce) / DOOR_W + 0.5, 1.0 - (q[2] - z0) / DOOR_H) for q in poly]
        polys.append((lifted, uvs))
        f = max(q[0] * dl[0] + q[1] * dl[1] for q in poly) - cd
        front = f if front is None else max(front, f)
    return polys, (front or 0.0)


_WALK = {}


def _walk_height():
    """Height of the wall walk above the wall's base: top of the wall's solid collision part
    (the UCX body from the foundation up to the walkway)."""
    if "z" in _WALK:
        return _WALK["z"]
    z = 1080.0
    try:
        col = _src(_col_path(WALL_MESH))
        if col and gs("get_num_triangle_i_ds")(col) > 0:
            r = gs("split_mesh_by_components")(col, unreal.DynamicMeshPool())
            best = None
            for part in (r[1] if isinstance(r, tuple) else r):
                b = gs("get_mesh_bounding_box")(part)
                b = b[0] if isinstance(b, tuple) else b
                if best is None or b.min.z < best.min.z:
                    best = b
            if best is not None and best.max.z > 50.0:
                z = float(best.max.z)
    except Exception as e:  # noqa
        unreal.log_warning("Walls: wall walk height not read (%s), using %.0f" % (e, z))
    _WALK["z"] = z
    return z


def _place_doors(actor, doors):
    """doors: [(tower path, tower transform (actor space), tower yaw, wall point (actor space),
    direction the wall leaves in (actor space, unit), tower index, wall slope)] - one per wall
    meeting a tower. Cuts each door picture out of its tower; _door_meshes makes them."""
    walk = _walk_height()
    frames = []
    for path, xf, yaw_deg, pt, d, tower, slope in doors:
        yaw = math.radians(yaw_deg)
        cy, sy = math.cos(yaw), math.sin(yaw)
        loc = xf.translation
        dl = (d[0] * cy + d[1] * sy, -d[0] * sy + d[1] * cy)      # into the tower's own space
        rx, ry = pt[0] - loc.x, pt[1] - loc.y
        c0 = (rx * cy + ry * sy, -rx * sy + ry * cy)
        # the sill sits on the wall walk where it meets the tower face: on a ramp that is higher
        # or lower than at the point itself (find the face first, then cut the door there)
        polys, front = _door_patch(path, dl, c0, pt[2] - loc.z + walk)
        if not polys:
            continue                                  # the wall doesn't reach a tower face here
        rise = slope * front
        if abs(rise) > 0.5:
            polys, front = _door_patch(path, dl, c0, pt[2] - loc.z + walk + rise)
            if not polys:
                continue
        world = [([(loc.x + q[0] * cy - q[1] * sy, loc.y + q[0] * sy + q[1] * cy, loc.z + q[2]) for q in poly], uvs)
                 for poly, uvs in polys]
        base = (pt[0] + d[0] * front, pt[1] + d[1] * front, pt[2] + walk + rise)   # door sill, middle
        frames.append({"base": base, "dir": d, "tower": tower, "slope": slope, "polys": world})
    _door_meshes(actor, frames)


def _ensure_uv(m):
    try:
        if gs("get_num_uv_sets")(m) < 1:
            gs("set_num_uv_sets")(m, 1)
    except Exception:
        pass


def _set_uv(m, tid, uvs):
    tri = unreal.GeometryScriptUVTriangle()
    for k, uv in zip(("uv0", "uv1", "uv2"), uvs):
        tri.set_editor_property(k, unreal.Vector2D(*uv))
    gs("set_mesh_triangle_u_vs")(m, 0, tid, tri, True)


DOOR_BOX_PREFIX = "TowerDoorBox_"          # boxes of an earlier version (switched off)
DOOR_EXIT = (160.0, 100.0)               # where you come out: this far in front of the tower wall, this high


def _try_set(obj, prop, val):
    try:
        if obj.get_editor_property(prop) != val:
            obj.set_editor_property(prop, val)
    except Exception as e:  # noqa
        unreal.log_warning("Walls: %s not set on %s (%s)" % (prop, obj.get_name(), e))


def _door_meshes(actor, frames):
    """Each door is its own mesh on the wall actor (TowerDoors_N, tag TowerDoor): the picture,
    and what you look at - only line traces (Visibility, Camera) hit it, on its exact shape;
    nothing bumps into it. The lists the Blueprint uses: DoorBoxes[i] (the door meshes) and
    DoorTargets[i] = where door i leads: through the tower, out of the tower's other wall door
    (world space, facing out along that wall). A door with no partner (a tower with only one
    wall) is not made."""
    by_tower = {}
    for k, f in enumerate(frames):
        by_tower.setdefault(f["tower"], []).append(k)
    partner = {}
    for ks in by_tower.values():
        for n, k in enumerate(ks):
            if len(ks) > 1:
                partner[k] = ks[(n + 1) % len(ks)]
    live = [k for k in range(len(frames)) if k in partner]
    comps = _instance_comps(actor, unreal.DynamicMeshComponent, DOOR_COMP_PREFIX, len(live)) if live else \
        [c for c in actor.get_components_by_class(unreal.DynamicMeshComponent) if c.get_name().startswith(DOOR_COMP_PREFIX)]
    mat = EAL.load_asset(DOOR_MAT) if EAL.does_asset_exist(DOOR_MAT) else None
    xf = actor.get_actor_transform()
    ayaw = xf.rotation.rotator().yaw
    used, targets = [], []
    for n, c in enumerate(comps):
        m = c.get_dynamic_mesh()
        m.reset()
        if n >= len(live):                           # spare (door removed): empty, no collision
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            c.set_editor_property("component_tags", [])
            try:
                c.notify_mesh_modified()
            except Exception:
                pass
            continue
        f = frames[live[n]]
        for poly, uvs in f["polys"]:
            ids = []
            for q in poly:
                r = gs("add_vertex_to_mesh")(m, unreal.Vector(*q), False)
                ids.append(r[1] if isinstance(r, tuple) else r)
            for k in range(1, len(ids) - 1):
                r = gs("add_triangle_to_mesh")(m, unreal.IntVector(ids[0], ids[k], ids[k + 1]), 0, False)
                tid = r[1] if isinstance(r, tuple) else r
                _ensure_uv(m)
                _set_uv(m, tid, [uvs[0], uvs[k], uvs[k + 1]])
        try:
            import sewer_builder
            sewer_builder._normals(m)
        except Exception:
            pass
        if mat and c.get_material(0) != mat:
            c.set_material(0, mat)
        c.set_editor_property("cast_shadow", False)
        for prop, val in (("enable_complex_collision", True),
                          ("collision_type", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)):
            _try_set(c, prop, val)
        c.set_collision_profile_name("Custom")
        c.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
        c.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
        c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY, unreal.CollisionResponseType.ECR_BLOCK)
        c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA, unreal.CollisionResponseType.ECR_BLOCK)
        _try_set(c, "generate_overlap_events", False)
        c.set_editor_property("component_tags", [unreal.Name("TowerDoor")])
        try:
            c.notify_mesh_modified()
            c.update_collision(False)
        except Exception:
            pass
        used.append(c)
        t = frames[partner[live[n]]]
        (tx, ty, tz), (ux, uy) = t["base"], t["dir"]
        local = unreal.Vector(tx + ux * DOOR_EXIT[0], ty + uy * DOOR_EXIT[0],
                              tz + t["slope"] * DOOR_EXIT[0] + DOOR_EXIT[1])
        targets.append(unreal.Transform(location=unreal.MathLibrary.transform_location(xf, local),
                                        rotation=unreal.Rotator(roll=0.0, pitch=0.0,
                                                                yaw=math.degrees(math.atan2(uy, ux)) + ayaw)))
    # the boxes of the earlier version: switched off (removing components from Python can crash)
    for c in actor.get_components_by_class(unreal.BoxComponent):
        if c.get_name().startswith(DOOR_BOX_PREFIX):
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            c.set_editor_property("component_tags", [])
            c.set_box_extent(unreal.Vector(1.0, 1.0, 1.0), True)

    def same_t(a, b):
        return len(a) == len(b) and all(
            (x.translation - y.translation).length() < 0.5 and abs(x.rotation.rotator().yaw - y.rotation.rotator().yaw) < 0.05
            for x, y in zip(a, b))
    try:
        # only when they change: setting them re-runs the Blueprint's construction script
        if [c.get_name() for c in (_prop(actor, "DoorBoxes", []) or []) if c] != [c.get_name() for c in used]:
            actor.set_editor_property("DoorBoxes", used)
        if not same_t(list(_prop(actor, "DoorTargets", []) or []), targets):
            actor.set_editor_property("DoorTargets", targets)
    except Exception as e:  # noqa
        unreal.log_warning("Walls: door lists not set - run walls_spline.make_blueprint() (%s)" % e)


# --------------------------------------------------------------------------- live updates
_STATE = {"sig": {}, "handle": None, "last": 0.0, "scan": 0.0, "actors": [], "pos": {}}


def _is_wall(a):
    try:
        return a.get_class().get_name() == "BP_WallSpline_C"
    except Exception:
        return False


def _signature(a):
    spline = a.get_component_by_class(unreal.SplineComponent)
    if not spline:
        return None
    n = spline.get_number_of_spline_points()
    pts = []
    for i in range(n):
        p = spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.LOCAL)
        pts.append((round(p.x, 1), round(p.y, 1), round(p.z, 1)))
    chunks = [c for c in a.get_components_by_class(unreal.DynamicMeshComponent) if c.get_name().startswith("WallChunk_")]
    empty = not chunks or gs("get_num_triangle_i_ds")(chunks[0].get_dynamic_mesh()) == 0
    chunks = len(chunks)
    t = a.get_actor_transform()
    where = (round(t.translation.x, 1), round(t.translation.y, 1), round(t.translation.z, 1),
             round(t.rotation.rotator().yaw, 2))
    return (tuple(pts), where, spline.is_closed_loop(), _path(_prop(a, "Tower", None)),
            tuple(_path(o) for o in (_prop(a, "TowerOverrides", []) or [])),
            tuple(round(float(r or 0.0), 2) for r in (_prop(a, "TowerRotations", []) or [])),
            tuple(bool(x) for x in (_prop(a, "NoWall", []) or [])),
            empty, chunks)


def _tick(dt):
    now = time.time()
    if now - _STATE["last"] < 0.1:
        return
    _STATE["last"] = now
    try:
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if editor.get_game_world():
            return                                   # not while playing
        # World teardown during a map switch leaves CurrentWorld unset for a
        # short time; do not query the actor subsystem until a new editor world exists.
        if editor.get_editor_world() is None:
            return
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        if now - _STATE["scan"] > 2.0:
            _STATE["scan"] = now
            _STATE["actors"] = [a for a in eas.get_all_level_actors() if _is_wall(a)]
        actors = [a for a in eas.get_selected_level_actors() if _is_wall(a)]
        if now - _STATE["scan"] < 0.15:              # right after a scan: check every wall once
            actors = _STATE["actors"]
        for a in actors:
            key = a.get_path_name()
            sig = _signature(a)
            if sig is not None and _STATE["sig"].get(key) != sig:
                before = list(_STATE.get("joins", {}).get(key, []))
                rebuild(a)
                _STATE["sig"][key] = _signature(a)
                # walls joined to it (before or after the edit) re-cut their corner to match
                seen = set()
                for o in before + list(_STATE.get("joins", {}).get(key, [])):
                    ok = o.get_path_name()
                    if ok in seen or ok == key:
                        continue
                    seen.add(ok)
                    try:
                        rebuild(o)
                        _STATE["sig"][ok] = _signature(o)
                    except Exception as e:  # noqa
                        unreal.log_warning("Walls: joined wall not updated (%s)" % e)
    except Exception as e:  # never break the editor tick
        unreal.log_warning("Walls live update: %s" % e)


def start():
    stop()
    _STATE["handle"] = unreal.register_slate_post_tick_callback(_tick)
    import builtins
    builtins._WALLS_TICK_HANDLE = _STATE["handle"]     # survives a reload of this script
    unreal.log("Walls: live wall updates on")


def stop():
    import builtins
    for h in (_STATE["handle"], getattr(builtins, "_WALLS_TICK_HANDLE", None)):
        if h is not None:
            try:
                unreal.unregister_slate_post_tick_callback(h)
            except Exception:
                pass
    _STATE["handle"] = None
    builtins._WALLS_TICK_HANDLE = None


def reload_and_rebuild():
    """After changing this script: py import walls_spline; walls_spline.reload_and_rebuild()"""
    import importlib
    import sys
    mod = importlib.reload(sys.modules[__name__])
    mod.start()
    mod.rebuild_all()


def rebuild_all():
    _SRC.clear()
    _WALK.clear()
    _TRIS.clear()

    _STATE["sig"].clear()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if _is_wall(a):
            rebuild(a)


def demo(origin=(0.0, -20000.0, 9000.0)):
    """Spawns a test wall: straight run, 90 deg corner, a ramp up, a 45 deg turn, different towers."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if _is_wall(a) and (a.get_actor_label() == "Walls_Demo" or a.get_actor_label().startswith("BP_WallSpline")):
            eas.destroy_actor(a)
    cls = unreal.EditorAssetLibrary.load_blueprint_class(BP_PATH)
    a = eas.spawn_actor_from_class(cls, unreal.Vector(*origin))
    a.set_actor_label("Walls_Demo")
    L = EAL.load_asset
    a.set_editor_property("Tower", L(MESHES + "/SM_Tower_Square_3"))
    a.set_editor_property("TowerOverrides", [L(MESHES + "/SM_Tower_Round_3"), None, L(MESHES + "/SM_Tower_Square_4"),
                                             L(MESHES + "/SM_Tower_Round_4"), None, L(MESHES + "/SM_Tower_Beacon")])
    sp = a.get_component_by_class(unreal.SplineComponent)
    pts = [(0, 0, 0), (4600, 0, 0), (4600, 4600, 0), (4600, 9200, 1500), (7800, 12400, 1500), (12000, 12400, 1500)]
    sp.clear_spline_points(False)
    for p in pts:
        sp.add_spline_point(unreal.Vector(*p), unreal.SplineCoordinateSpace.LOCAL, False)
    _mark_edited(sp)
    sp.update_spline()
    rebuild(a)
    n = gs("get_num_triangle_i_ds")(a.get_component_by_class(unreal.DynamicMeshComponent).get_dynamic_mesh())
    unreal.log("Walls demo: %d triangles" % n)
    return a
