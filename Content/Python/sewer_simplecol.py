"""Simple collision for hollow sewer pieces (Zippy). Collision setting: project default
(simple and complex); everything stays walkable inside.

  passage pieces   7 boxes from the passage profile: channel floor, two walkway blocks, two walls,
                   two roof boxes lying along the vault
  end walls/caps   one convex hull (they are solid)
  crossings/rooms  only their INSIDE surfaces count (found by casting rays through the mesh):
                   floors -> blocks reaching down, walls -> slabs behind them (reaching a bit
                   higher), vaults -> slabs above them. Each surface is split into as few convex
                   pieces as possible.
  water            a slab under the surface (overlap only)

    py import importlib, sewer_simplecol; importlib.reload(sewer_simplecol); sewer_simplecol.apply_assets()
"""
import math
import os
import unreal

PY_DIR = os.path.dirname(os.path.abspath(__file__))
EAL = unreal.EditorAssetLibrary
THICKNESS = 20.0        # cm each slab reaches behind its surface
PATCH_ANGLE = 8.0       # deg: neighbouring faces closer than this share one slab
WATER_THICKNESS = 30.0  # water slabs reach this far under the surface
MIN_WIDTH = 2.0         # cm: thinner faces get no slab (their neighbours cover them)

ASSETS = ["/Game/Sewers/Meshes/v2/" + n for n in (
    "Passage12test", "Passage20test", "Passage12endtest", "Passage20endtest",
    "Water12test", "Water20test")]
FLOOR_DEPTH = 150.0     # floors: block reaching this far down
WALL_DEPTH = 40.0       # walls: slab this thick behind the face
WALL_RAISE = 150.0      # walls: slab reaches this far above the face (covers the vault spring)
ROOF_DEPTH = 60.0       # vaults/ceilings: slab this thick above the face
ROOF_BOX = 150.0        # passage roof boxes: thickness


def gs(name):
    import sewer_builder
    return sewer_builder.gs(name)


def _v(r):
    return r[0] if isinstance(r, tuple) else r


def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    L = math.sqrt(_dot(a, a))
    return (a[0] / L, a[1] / L, a[2] / L) if L > 1e-9 else None


def _hull2d(pts):
    pts = sorted(set((round(x, 3), round(y, 3)) for x, y in pts))
    if len(pts) < 3:
        return pts

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def _area2d(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly)))) / 2.0


def _mesh_data(dm):
    """Triangles as (vertex ids, positions, outward normal as Unreal shows it)."""
    tris = []
    flip = None
    for t in range(gs("get_num_triangle_i_ds")(dm)):
        ids = _v(gs("get_triangle_indices")(dm, t))
        ps = [p for p in gs("get_triangle_positions")(dm, t) if isinstance(p, unreal.Vector)]
        if len(ps) < 3:
            continue
        P = [(p.x, p.y, p.z) for p in ps]
        # Unreal is left-handed: its face normal is the mirror of the usual cross product
        n = _norm(_cross(_sub(P[2], P[0]), _sub(P[1], P[0])))
        if n is None:
            continue
        if flip is None:        # check the handedness once against Unreal's own face normal
            fn = _v(gs("get_triangle_face_normal")(dm, t))
            flip = (fn.x * n[0] + fn.y * n[1] + fn.z * n[2]) < 0
        if flip:
            n = (-n[0], -n[1], -n[2])
        tris.append(((ids.x, ids.y, ids.z), P, n))
    return tris


def _patches(tris):
    """Groups edge-connected triangles whose normals stay within PATCH_ANGLE of the first one."""
    cosmax = math.cos(math.radians(PATCH_ANGLE))
    by_edge = {}
    for k, (ids, _, _) in enumerate(tris):
        for a, b in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            by_edge.setdefault((min(a, b), max(a, b)), []).append(k)
    seen, out = set(), []
    for k in range(len(tris)):
        if k in seen:
            continue
        n0 = tris[k][2]
        group, stack = [], [k]
        seen.add(k)
        while stack:
            j = stack.pop()
            group.append(j)
            ids = tris[j][0]
            for a, b in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
                for o in by_edge.get((min(a, b), max(a, b)), []):
                    if o not in seen and _dot(tris[o][2], n0) >= cosmax:
                        seen.add(o)
                        stack.append(o)
        out.append(group)
    return out


def _slab(points, n, depth):
    """Convex slab: the points' outline in the plane facing n, pushed `depth` behind it."""
    u = _norm(_cross(n, (0.0, 0.0, 1.0)) if abs(n[2]) < 0.9 else _cross(n, (1.0, 0.0, 0.0)))
    w = _cross(n, u)
    top = max(_dot(p, n) for p in points)          # the plane on the open side of the patch
    poly = _hull2d([(_dot(p, w), _dot(p, u)) for p in points])     # (forward, right) of the frame below
    if len(poly) < 3 or _area2d(poly) < 1.0:
        return None
    # slivers make degenerate hulls, and one bad hull stops the whole mesh's collision cooking
    longest = max(math.hypot(poly[i][0] - poly[i - 1][0], poly[i][1] - poly[i - 1][1]) for i in range(len(poly)))
    if 2.0 * _area2d(poly) / max(longest, 1e-6) < MIN_WIDTH:
        return None
    m = unreal.DynamicMesh()
    base = [(n[i] * top) for i in range(3)]
    # frame: forward w, right u, up -n (w x u = -n, a proper rotation); polygon at `top`,
    # extruded along local +Z = into the wall
    xf = unreal.Transform(location=unreal.Vector(*base),
                          rotation=unreal.MathLibrary.make_rotation_from_axes(
                              unreal.Vector(*w), unreal.Vector(*u), unreal.Vector(-n[0], -n[1], -n[2])))
    gs("append_simple_extrude_polygon")(m, unreal.GeometryScriptPrimitiveOptions(), xf,
                                        [unreal.Vector2D(x, y) for x, y in poly], float(depth), 0, True,
                                        unreal.GeometryScriptPrimitiveOriginMode.BASE)
    return m


def build(dm, depth=THICKNESS):
    """Simple-collision shapes for a dynamic mesh: one convex slab per patch (per triangle where
    a patch isn't convex, so no slab spans an opening)."""
    tris = _mesh_data(dm)
    o = unreal.GeometryScriptCollisionFromMeshOptions()
    o.set_editor_property("method", unreal.GeometryScriptCollisionGenerationMethod.CONVEX_HULLS)
    o.set_editor_property("max_convex_hulls_per_mesh", 1)
    o.set_editor_property("simplify_hulls", False)
    o.set_editor_property("auto_detect_boxes", False)
    shapes = []

    def add(points, n):
        m = _slab(points, n, depth)
        if m is not None:
            c = gs("generate_collision_from_mesh")(m, o)
            shapes.append(c[0] if isinstance(c, tuple) else c)

    for group in _patches(tris):
        nsum = [0.0, 0.0, 0.0]
        area, pts = 0.0, []
        for j in group:
            P, n = tris[j][1], tris[j][2]
            a = 0.5 * math.sqrt(_dot(_cross(_sub(P[1], P[0]), _sub(P[2], P[0])), _cross(_sub(P[1], P[0]), _sub(P[2], P[0]))))
            area += a
            for i in range(3):
                nsum[i] += n[i] * a
            pts += P
        n = _norm(tuple(nsum))
        if n is None or area < 1.0:
            continue
        u = _norm(_cross(n, (0.0, 0.0, 1.0)) if abs(n[2]) < 0.9 else _cross(n, (1.0, 0.0, 0.0)))
        w = _cross(n, u)
        hull = _hull2d([(_dot(p, u), _dot(p, w)) for p in pts])
        if len(hull) >= 3 and _area2d(hull) <= area * 1.02 + 1.0:
            add(pts, n)                                   # convex patch: one slab
        else:
            for j in group:                               # not convex: a slab per triangle
                add(tris[j][1], tris[j][2])
    total = gs("combine_simple_collision_array")(shapes) if shapes else unreal.GeometryScriptSimpleCollision()
    return (total[0] if isinstance(total, tuple) else total), len(shapes)


# --------------------------------------------------------------------------- shared helpers
def _opts(hulls=1):
    o = unreal.GeometryScriptCollisionFromMeshOptions()
    o.set_editor_property("method", unreal.GeometryScriptCollisionGenerationMethod.CONVEX_HULLS)
    o.set_editor_property("max_convex_hulls_per_mesh", hulls)
    o.set_editor_property("simplify_hulls", False)
    o.set_editor_property("auto_detect_boxes", False)
    return o


def _hull_of(m):
    c = gs("generate_collision_from_mesh")(m, _opts())
    return c[0] if isinstance(c, tuple) else c


def _combine(shapes):
    total = gs("combine_simple_collision_array")(shapes) if shapes else unreal.GeometryScriptSimpleCollision()
    return total[0] if isinstance(total, tuple) else total


def _prism(poly_yz, x0, x1):
    """Convex (Y, Z) polygon extruded along X from x0 to x1."""
    m = unreal.DynamicMesh()
    import sewer_builder as sb
    sb._append_prism(m, sb._oriented([tuple(p) for p in poly_yz]), unreal.Vector(x0, 0, 0), unreal.Vector(1, 0, 0), x1 - x0)
    return m


# --------------------------------------------------------------------------- passages
def passage_polys(ptype):
    """The 7 cross-section pieces of a passage type, from its profiles: channel floor, walkway
    blocks, walls and two roof boxes along the vault (their inner faces never cross the void)."""
    import sewer_builder as sb
    cfg = sb.PASSAGE_TYPES[ptype]
    void, solid = cfg["void_profile"], cfg["solid_profile"]
    cw = max(abs(y) for y, z in void if z < -1)                 # channel half width
    ch = min(z for y, z in void)                                 # channel floor
    ww = max(abs(y) for y, z in void if abs(z) < 1)              # walkway outer edge (wall face)
    sy = max(abs(y) for y, z in solid)
    sz0, sz1 = min(z for y, z in solid), max(z for y, z in solid)
    polys = [[(-cw, sz0), (cw, sz0), (cw, ch), (-cw, ch)]]
    for s in (-1, 1):
        polys.append([(s * sy, sz0), (s * cw, sz0), (s * cw, 0.0), (s * sy, 0.0)])          # walkway block
        polys.append([(s * sy, 0.0), (s * ww, 0.0), (s * ww, sz1), (s * sy, sz1)])          # wall
        # roof: along the vault facet on this side that leans closest to 45 degrees
        best = None
        n = len(void)
        for k in range(n):
            (y0, z0), (y1, z1) = void[k], void[(k + 1) % n]
            if min(z0, z1) < 1 or (y0 + y1) * s <= 0:
                continue
            dy, dz = y1 - y0, z1 - z0
            L = math.hypot(dy, dz)
            if L < 1:
                continue
            score = abs(abs(dz / L) - math.sqrt(0.5))
            if best is None or score < best[0]:
                best = (score, (y0, z0), (dy / L, dz / L))
        if best is None:
            continue
        _, (y0, z0), (ty, tz) = best
        nrm = (-tz, ty) if (-tz * s + ty) > 0 else (tz, -ty)     # pointing up/outwards, away from the void
        # the facet line, from the wall face to a little past the middle
        def at(y):
            return (y, z0 + (y - y0) * tz / ty) if abs(ty) > 1e-6 else (y, z0)
        a, b = at(s * ww), at(-s * 20.0)
        polys.append([a, b, (b[0] + nrm[0] * ROOF_BOX, b[1] + nrm[1] * ROOF_BOX),
                      (a[0] + nrm[0] * ROOF_BOX, a[1] + nrm[1] * ROOF_BOX)])
    return polys


def passage_collision(sm, ptype):
    b = sm.get_bounding_box()
    shapes = [_hull_of(_prism(p, b.min.x, b.max.x)) for p in passage_polys(ptype)]
    return _combine(shapes), len(shapes)


# --------------------------------------------------------------------------- crossings / rooms
def _ray_hits(grid, cell, tris, origin, d, maxd):
    """Does a ray hit any of the mesh triangles within maxd? (grid = xy cell -> triangle ids)"""
    seen = set()
    steps = int(maxd / (cell * 0.5)) + 2
    for k in range(steps):
        t = k * cell * 0.5
        cx, cy = int(math.floor((origin[0] + d[0] * t) / cell)), int(math.floor((origin[1] + d[1] * t) / cell))
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for ti in grid.get((gx, gy), ()):
                    if ti in seen:
                        continue
                    seen.add(ti)
                    P = tris[ti][1]
                    e1, e2 = _sub(P[1], P[0]), _sub(P[2], P[0])
                    h = _cross(d, e2)
                    a = _dot(e1, h)
                    if abs(a) < 1e-9:
                        continue
                    f = 1.0 / a
                    s = _sub(origin, P[0])
                    u = f * _dot(s, h)
                    if u < 0 or u > 1:
                        continue
                    q = _cross(s, e1)
                    v = f * _dot(d, q)
                    if v < 0 or u + v > 1:
                        continue
                    tt = f * _dot(e2, q)
                    if 1.0 < tt < maxd:
                        return True
    return False


def _convex_pieces(tris, group, n):
    """Splits a flat patch into few convex polygons (merging neighbouring triangles while the
    result stays convex). Returns lists of 3D points."""
    u = _norm(_cross(n, (0.0, 0.0, 1.0)) if abs(n[2]) < 0.9 else _cross(n, (1.0, 0.0, 0.0)))
    w = _cross(n, u)
    pos = {}
    polys = []
    for j in group:
        ids, P, _ = tris[j]
        for vid, p in zip(ids, P):
            pos[vid] = p
        poly = list(ids)
        a = [(_dot(pos[v], u), _dot(pos[v], w)) for v in poly]
        if (a[1][0] - a[0][0]) * (a[2][1] - a[0][1]) - (a[1][1] - a[0][1]) * (a[2][0] - a[0][0]) < 0:
            poly.reverse()
        polys.append(poly)
    P2 = {v: (_dot(p, u), _dot(p, w)) for v, p in pos.items()}

    def convex(poly):
        m = len(poly)
        for i in range(m):
            a, b, c = P2[poly[i - 1]], P2[poly[i]], P2[poly[(i + 1) % m]]
            if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) < -1e-3:
                return False
        return True
    changed = True
    while changed:
        changed = False
        edges = {}
        for pi, poly in enumerate(polys):
            if poly is None:
                continue
            for k in range(len(poly)):
                edges[(poly[k], poly[(k + 1) % len(poly)])] = pi
        for (a, b), pi in list(edges.items()):
            qi = edges.get((b, a))
            if qi is None or qi == pi or polys[pi] is None or polys[qi] is None:
                continue
            p, q = polys[pi], polys[qi]
            ia, iq = p.index(a), q.index(b)
            # p: ... a b ... ; q: ... b a ... -> walk p from b round to a, then q from a round to b
            pp = p[p.index(b):] + p[:p.index(b)]          # starts at b, ends at a
            qq = q[q.index(a):] + q[:q.index(a)]          # starts at a, ends at b
            merged = pp[:-1] + qq[:-1]
            if len(set(merged)) == len(merged) and convex(merged):
                polys[pi], polys[qi] = merged, None
                changed = True
                break
    return [[pos[v] for v in poly] for poly in polys if poly]


def node_collision(dm):
    tris = _mesh_data(dm)
    cell = 100.0
    grid = {}
    for ti, (_, P, _) in enumerate(tris):
        xs, ys = [p[0] for p in P], [p[1] for p in P]
        for gx in range(int(math.floor(min(xs) / cell)), int(math.floor(max(xs) / cell)) + 1):
            for gy in range(int(math.floor(min(ys) / cell)), int(math.floor(max(ys) / cell)) + 1):
                grid.setdefault((gx, gy), []).append(ti)
    shapes = []

    def add(points, n, depth):
        m = _slab(points, n, depth)
        if m is not None:
            shapes.append(_hull_of(m))

    for group in _patches(tris):
        nsum, area = [0.0, 0.0, 0.0], 0.0
        for j in group:
            P, nn = tris[j][1], tris[j][2]
            cr = _cross(_sub(P[1], P[0]), _sub(P[2], P[0]))
            a = 0.5 * math.sqrt(_dot(cr, cr))
            area += a
            for k in range(3):
                nsum[k] += nn[k] * a
        n = _norm(tuple(nsum))
        if n is None or area < 4.0:
            continue
        # inside surfaces only: looking out along the normal they see the opposite side
        j = max(group, key=lambda j: 0.5 * math.sqrt(_dot(_cross(_sub(tris[j][1][1], tris[j][1][0]), _sub(tris[j][1][2], tris[j][1][0])),
                                                           _cross(_sub(tris[j][1][1], tris[j][1][0]), _sub(tris[j][1][2], tris[j][1][0])))))
        P = tris[j][1]
        c = tuple((P[0][k] + P[1][k] + P[2][k]) / 3.0 + n[k] * 0.5 for k in range(3))
        if not _ray_hits(grid, cell, tris, c, n, 1500.0):
            continue
        if n[2] > 0.5:
            kind, depth = "floor", FLOOR_DEPTH
        elif n[2] < -0.3:
            kind, depth = "roof", ROOF_DEPTH
        else:
            kind, depth = "wall", WALL_DEPTH
        for piece in _convex_pieces(tris, group, n):
            if kind == "wall":
                piece = piece + [(p[0], p[1], p[2] + WALL_RAISE) for p in piece]
            add(piece, n, depth)
    return _combine(shapes), len(shapes)


def solid_collision(dm):
    return _hull_of(dm), 1


def apply_to(sm, depth=None):
    """Replaces a static mesh's simple collision (see the module notes); trace = project default."""
    name = sm.get_name()
    dm = unreal.DynamicMesh()
    gs("copy_mesh_from_static_mesh")(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                     unreal.GeometryScriptMeshReadLOD())
    if "Water" in name:
        col, count = build(dm, depth or WATER_THICKNESS)
    elif name.startswith("SM_SewerNode"):
        col, count = node_collision(dm)
    elif name.startswith("Passage") and "end" not in name.lower():
        col, count = passage_collision(sm, "P20" if "20" in name else "P12")
    elif "end" in name.lower() or "Cap" in name:
        col, count = solid_collision(dm)
    else:
        col, count = node_collision(dm)
    gs("set_simple_collision_of_static_mesh")(col, sm, unreal.GeometryScriptSetSimpleCollisionOptions())
    bs = sm.get_editor_property("body_setup")
    if bs:
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
    EAL.save_asset(sm.get_path_name().split(".")[0], only_if_is_dirty=False)
    return count


def apply_assets(extra_folder="/Game/Sewers/Generated", level_only=True):
    """The modelled kit pieces, plus every generated mesh used in the open level."""
    paths = [p for p in ASSETS if EAL.does_asset_exist(p)]
    if extra_folder:
        used = set()
        if level_only:
            eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            for a in eas.get_all_level_actors():
                for c in a.get_components_by_class(unreal.StaticMeshComponent):
                    sm = c.get_editor_property("static_mesh")
                    if sm and sm.get_path_name().startswith(extra_folder):
                        used.add(sm.get_path_name().split(".")[0])
        paths += sorted(used)
    log = []
    for p in paths:
        sm = EAL.load_asset(p)
        try:
            log.append("%s: %d slabs" % (p.split("/")[-1], apply_to(sm)))
        except Exception as e:
            log.append("%s: FAILED %s" % (p, e))
        open(os.path.join(PY_DIR, "scan_out.txt"), "w").write("\n".join(log))
    _refresh_level()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log.append("done")
    open(os.path.join(PY_DIR, "scan_out.txt"), "w").write("\n".join(log))
    return log


def _refresh_level():
    """Instanced components only pick up new collision when collision is switched on afresh."""
    import sewer_builder
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.get_editor_property("static_mesh")
            if not sm or not sm.get_path_name().startswith("/Game/Sewers/"):
                continue
            if "Water" in c.get_name():
                sewer_builder._water_collision(c)
            else:
                prof = c.get_collision_profile_name()
                c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                c.set_collision_profile_name(prof)
                c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
