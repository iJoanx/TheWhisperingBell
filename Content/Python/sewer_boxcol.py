"""Box collision for the sewer kit (Zippy): a handful of convex blocks per passage cross-section
(walkways, channel floor, walls, springers, two roof blocks, crown), placed around the
walkable space so it stays open. Used for the passage pieces and for crossings (each arm's
blocks, level through the hub, mitred into the slope, cut on the crossing's mitre lines).

    py import importlib, sewer_boxcol; importlib.reload(sewer_boxcol); sewer_boxcol.apply_passages()
"""
import math
import unreal

EAL = unreal.EditorAssetLibrary


def _mirror(polys):
    out = []
    for p in polys:
        out.append(p)
        out.append([(-y, z) for (y, z) in reversed(p)])
    return out


# convex (Y, Z) polygons, counter-clockwise; left-side ones are mirrored to the right
COLLISION_PROFILES = {
    "P12": _mirror([
        [(-220, -200), (-60, -200), (-60, 0), (-220, 0)],                 # walkway block
        [(-220, 0), (-120, 0), (-120, 250), (-220, 250)],                 # wall
        [(-220, 250), (-120, 250), (-104, 310), (-220, 310)],             # springer
        # roof in two pieces following the vault (one straight slab from the springer to the crown
        # left an empty pocket under it, up to 44 cm at the crown)
        [(-220, 310), (-104, 310), (-60, 354), (-60, 474), (-220, 474)],  # roof, lower vault
        [(-60, 354), (0, 370), (0, 474), (-60, 474)],                     # roof, crown half
    ]) + [
        [(-60, -200), (60, -200), (60, -100), (-60, -100)],               # channel floor
    ],
    "P20": _mirror([
        [(-300, -200), (-100, -200), (-100, 0), (-300, 0)],
        [(-300, 0), (-200, 0), (-200, 350), (-300, 350)],
        [(-300, 350), (-200, 350), (-173, 450), (-300, 450)],
        [(-300, 450), (-173, 450), (-100, 523), (-100, 654), (-300, 654)],   # roof, lower vault
        [(-100, 523), (0, 550), (0, 654), (-100, 654)],                      # roof, crown half
    ]) + [
        [(-100, -200), (100, -200), (100, -100), (-100, -100)],
    ],
}


def gs(name):
    import sewer_builder
    return sewer_builder.gs(name)


# ----------------------------------------------------------------------------- tiny 3D maths
def _add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    L = math.sqrt(_dot(a, a))
    return _mul(a, 1.0 / L) if L > 1e-12 else a


def _vertices(planes, eps=1e-3):
    """Corners of the convex polytope {p : n.p <= d for every (n, d)}."""
    out = []
    k = len(planes)
    for i in range(k):
        for j in range(i + 1, k):
            for l in range(j + 1, k):
                n1, d1 = planes[i]
                n2, d2 = planes[j]
                n3, d3 = planes[l]
                c23 = _cross(n2, n3)
                det = _dot(n1, c23)
                if abs(det) < 1e-9:
                    continue
                p = _mul(_add(_add(_mul(c23, d1), _mul(_cross(n3, n1), d2)), _mul(_cross(n1, n2), d3)), 1.0 / det)
                if all(_dot(n, p) <= d + eps for n, d in planes):
                    if not any(_dot(_sub(p, q), _sub(p, q)) < 0.01 for q in out):
                        out.append(p)
    return out


def _hull_tris(pts):
    """Faces of the convex hull of a few points: every supporting plane once, fan-triangulated
    (no duplicate or overlapping triangles - those split the shape into extra hulls)."""
    n = len(pts)
    c = _mul(tuple(sum(p[i] for p in pts) for i in range(3)), 1.0 / n)
    faces = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                nrm = _cross(_sub(pts[j], pts[i]), _sub(pts[k], pts[i]))
                L = math.sqrt(_dot(nrm, nrm))
                if L < 1e-6:
                    continue
                nrm = _mul(nrm, 1.0 / L)
                if _dot(nrm, _sub(c, pts[i])) > 0:
                    nrm = _mul(nrm, -1.0)                 # outward
                d = _dot(nrm, pts[i])
                if any(_dot(nrm, p) > d + 1e-3 for p in pts):
                    continue                              # not a supporting plane
                if any(_dot(nrm, f[0]) > 1 - 1e-6 and abs(f[1] - d) < 1e-3 for f in faces):
                    continue                              # this face already found
                faces.append((nrm, d))
    tris = []
    for nrm, d in faces:
        on = [i for i, p in enumerate(pts) if abs(_dot(nrm, p) - d) < 1e-3]
        fc = _mul(tuple(sum(pts[i][a] for i in on) for a in range(3)), 1.0 / len(on))
        u = _unit(_sub(pts[on[0]], fc))
        w = _cross(nrm, u)
        on.sort(key=lambda i: math.atan2(_dot(_sub(pts[i], fc), w), _dot(_sub(pts[i], fc), u)))
        for t in range(1, len(on) - 1):
            tris.append((on[0], on[t + 1], on[t]))       # clockwise seen from outside = Unreal front
    return tris


MIN_THICKNESS = 2.0     # cm: thinner pieces are dropped (one degenerate hull stops the whole
                        # mesh's collision from cooking)


def _convex_shape(planes, opts):
    pts = _vertices(planes)
    if len(pts) < 4:
        return None
    for nrm, _ in planes:                    # width across every face direction
        ds = [_dot(nrm, p) for p in pts]
        if max(ds) - min(ds) < MIN_THICKNESS:
            return None
    m = unreal.DynamicMesh()
    ids = []
    for p in pts:
        r = gs("add_vertex_to_mesh")(m, unreal.Vector(*p), False)
        ids.append(r[1] if isinstance(r, tuple) else r)
    for t in _hull_tris(pts):
        gs("add_triangle_to_mesh")(m, unreal.IntVector(ids[t[0]], ids[t[1]], ids[t[2]]), 0, False)
    c = gs("generate_collision_from_mesh")(m, opts)
    return c[0] if isinstance(c, tuple) else c


def _opts():
    o = unreal.GeometryScriptCollisionFromMeshOptions()
    o.set_editor_property("method", unreal.GeometryScriptCollisionGenerationMethod.CONVEX_HULLS)
    o.set_editor_property("max_convex_hulls_per_mesh", 1)
    o.set_editor_property("simplify_hulls", False)
    o.set_editor_property("auto_detect_boxes", False)
    return o


def _prism_planes(poly, origin, ex, ey, ez, x0, x1):
    """Planes of a (Y,Z) polygon placed in the frame (origin, ex along, ey lateral, ez up),
    running from x0 to x1 along ex."""
    planes = []
    k = len(poly)
    for i in range(k):
        (y0, z0), (y1, z1) = poly[i], poly[(i + 1) % k]
        ny, nz = (z1 - z0), -(y1 - y0)                   # outward for a CCW polygon
        L = math.hypot(ny, nz)
        n = _unit(_add(_mul(ey, ny / L), _mul(ez, nz / L)))
        p = _add(origin, _add(_mul(ey, y0), _mul(ez, z0)))
        planes.append((n, _dot(n, p)))
    planes.append((_mul(ex, -1.0), -_dot(ex, _add(origin, _mul(ex, x0)))))
    planes.append((ex, _dot(ex, _add(origin, _mul(ex, x1)))))
    return planes


def _set(sm, shapes):
    total = gs("combine_simple_collision_array")(shapes) if shapes else unreal.GeometryScriptSimpleCollision()
    total = total[0] if isinstance(total, tuple) else total
    gs("set_simple_collision_of_static_mesh")(total, sm, unreal.GeometryScriptSetSimpleCollisionOptions())
    bs = sm.get_editor_property("body_setup")
    if bs:
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
    EAL.save_asset(sm.get_path_name().split(".")[0], only_if_is_dirty=False)
    return len(shapes)


# ----------------------------------------------------------------------------- passages
def passage_collision(sm, ptype):
    """A straight passage piece (runs along +X over its bounds)."""
    b = sm.get_bounding_box()
    o = _opts()
    shapes = []
    for poly in COLLISION_PROFILES[ptype]:
        s = _convex_shape(_prism_planes(poly, (0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1), b.min.x, b.max.x), o)
        if s is not None:
            shapes.append(s)
    return _set(sm, shapes)


def apply_passages():
    import sewer_builder as sb
    out = []
    for ptype, cfg in sb.PASSAGE_TYPES.items():
        if ptype in COLLISION_PROFILES and EAL.does_asset_exist(cfg["mesh"]):
            out.append("%s: %d blocks" % (cfg["mesh"].split("/")[-1], passage_collision(EAL.load_asset(cfg["mesh"]), ptype)))
    return out


# ----------------------------------------------------------------------------- crossings
def crossing_collision(sm, conns, hub):
    """conns: node-local connections (h, d, lead, pitch, ptype) as the builder uses them."""
    import sewer_builder as sb
    o = _opts()
    shapes = []
    bend = sb._bend_mitre(conns)
    mitres = {} if bend else sb._crossing_mitres(conns)
    for k, c in enumerate(conns):
        if c["ptype"] not in COLLISION_PROFILES:
            continue
        h = _unit((c["h"].x, c["h"].y, 0.0))
        ey = (-h[1], h[0], 0.0)
        d = _unit((c["d"].x, c["d"].y, c["d"].z))
        opposite = any(j != k and sb._angle_between(c, conns[j]) >= sb.OPPOSITE_DEG for j in range(len(conns)))
        if bend:
            sw = sb._solid_half_width(c["ptype"])
            back = max(sw, bend[k][0] + sw - sb._void_half_width(c["ptype"]))   # as the outer block
        else:
            back = 0.0 if opposite else sb._solid_half_width(c["ptype"])
        level = abs(c["pitch"]) < sb.GEOM_LEVEL_EPS_DEG
        kink = _mul(h, hub)
        nk = _unit(_add(h, d))                           # mitre between the level hub and the slope
        # outside of a slight kink in an almost straight run: that side's blocks reach back behind
        # the centre like an outer corner's (starting both at the centre left a wedge-shaped hole)
        kink_sides = []
        if opposite and not bend:
            for i_, j_, corner in sb._outer_corners(conns):
                if k in (i_, j_) and sb._angle_between(conns[i_], conns[j_]) >= sb.OPPOSITE_DEG:
                    kink_sides.append((corner[0], corner[1], 0.0))
        for poly in COLLISION_PROFILES[c["ptype"]]:
            side = sum(y for y, _ in poly) / len(poly)
            side_dir = _mul(ey, 1.0 if side > 0 else -1.0)
            back_p = back
            if abs(side) >= 1.0 and any(_dot(side_dir, cv) > 0 for cv in kink_sides):
                back_p = sb._solid_half_width(c["ptype"])
            clips = []
            variants = [[]]          # alternative extra cuts (each makes its own block)
            upper = min(z for _, z in poly) >= 0.0
            wk = sb._void_half_width(c["ptype"])
            if bend:
                pt, nrm = bend[k][1], bend[k][2]
                n3 = (nrm.x, nrm.y, 0.0)
                clips.append((n3, _dot(n3, (pt.x, pt.y, 0.0))))
            for (a, b2), (C, D, ref) in mitres.items():
                if k not in (a, b2):
                    continue
                other = conns[b2 if k == a else a]
                facing = abs(side) < 1.0 or _dot(side_dir, (other["h"].x, other["h"].y, 0.0)) > 0
                if not facing:
                    continue
                wo = sb._void_half_width(other["ptype"])
                ho = _unit((other["h"].x, other["h"].y, 0.0))
                eo = (-ho[1], ho[0], 0.0)
                if upper and wo > wk + 1.0:
                    # meeting a wider tunnel: walls and vault stop at the wider tunnel's wall line
                    sgn = 1.0 if _dot(eo, h) >= 0 else -1.0
                    clips.append((_mul(eo, -sgn), -wo))
                    continue
                if upper and wk > wo + 1.0:
                    # a narrower tunnel opens in this wall: keep the wall beside and above it
                    top = max(z for _, z in sb.PASSAGE_TYPES[other["ptype"]]["void_profile"])
                    variants = [v + [extra] for v in variants for extra in
                                ((eo, -wo), (_mul(eo, -1.0), -wo), ((0.0, 0.0, -1.0), -top))]
                    continue
                dx, dy = D[0] - C[0], D[1] - C[1]
                n2 = _unit((-dy, dx, 0.0))
                sref = _dot(n2, (ref[0] - C[0], ref[1] - C[1], 0.0))     # ref lies on arm a's side
                mine = (sref >= 0) == (k == a)
                n3 = n2 if not mine else _mul(n2, -1.0)                  # keep n3.p <= d on my side
                clips.append((n3, _dot(n3, (C[0], C[1], 0.0))))
            # the block reaches back behind the centre: keep it out of every NON-neighbouring
            # passage's walkable space too (with a third passage in between, a side wall reached
            # right across into the far passage's walkway); floor blocks only out of its channel
            if back_p > 0.0 and abs(side) >= 1.0 and not bend and len(conns) >= 3:
                neighbours = set()
                for (a, b2) in mitres:
                    if k in (a, b2):
                        neighbours.add(b2 if k == a else a)
                for j, cj in enumerate(conns):
                    if j == k or j in neighbours or cj["ptype"] not in COLLISION_PROFILES:
                        continue
                    if sb._angle_between(c, cj) >= sb.OPPOSITE_DEG:
                        continue
                    hj = _unit((cj["h"].x, cj["h"].y, 0.0))
                    eyj = (-hj[1], hj[0], 0.0)
                    t = _dot(h, eyj)
                    sg = (1.0 if t > 0 else -1.0) if abs(t) > 0.05 else (1.0 if _dot(side_dir, eyj) > 0 else -1.0)
                    wj = sb._void_half_width(cj["ptype"])
                    if max(z for _, z in poly) <= 0.5:
                        wj = sb.PASSAGE_TYPES[cj["ptype"]].get("water_half_width", wj)
                    # that passage's space is a strip on ITS side of the centre only: keep what is
                    # beside the strip, or behind where it starts
                    exs = [[(_mul(eyj, -sg), -wj)],           # sg * (p . eyj) >= wj
                           [(hj, 0.0)]]                       # p . hj <= 0
                    if min(z for _, z in poly) >= 0.0:
                        # walls / roof: also keep what is above that passage's ceiling or inside its
                        # own solid above the arch (cutting the roof wherever it passed over the
                        # other passage's strip left a hole in the ceiling at the centre)
                        topj = max(z for _, z in sb.PASSAGE_TYPES[cj["ptype"]]["void_profile"])
                        topj += (hub + cj["lead"]) * abs(math.tan(math.radians(cj["pitch"]))) + 2.0
                        exs.append([((0.0, 0.0, -1.0), -topj)])
                        dj = _unit((cj["d"].x, cj["d"].y, cj["d"].z))
                        ezj = _cross(dj, eyj)
                        for pj in COLLISION_PROFILES[cj["ptype"]]:
                            if min(z for _, z in pj) >= 1.0:
                                exs.append(_prism_planes(pj, (0.0, 0.0, 0.0), hj, eyj, (0.0, 0.0, 1.0),
                                                         -100000.0, 100000.0)[:-2])
                    variants = [v + ex_ for v in variants for ex_ in exs]
            parts = []
            if level:
                parts.append(_prism_planes(poly, (0.0, 0.0, 0.0), h, ey, (0, 0, 1), -back_p, hub + c["lead"]))
            else:
                lv = _prism_planes(poly, (0.0, 0.0, 0.0), h, ey, (0, 0, 1), -back_p, hub + c["lead"])
                lv.append((nk, _dot(nk, kink)))
                parts.append(lv)
                ez = _cross(d, ey)
                sl = _prism_planes(poly, kink, d, ey, ez, -c["lead"], c["lead"])
                sl.append((_mul(nk, -1.0), -_dot(nk, kink)))
                parts.append(sl)
            for planes in parts:
                for v in variants:
                    s = _convex_shape(planes + clips + v, o)
                    if s is not None:
                        shapes.append(s)
    # sharp corners (every arm on one side): the interior stops just behind the centre, so close
    # it there with one block behind every arm's start
    if not bend and conns:
        hs = [_unit((c["h"].x, c["h"].y, 0.0)) for c in conns]
        m = _unit(tuple(sum(h[i] for h in hs) for i in range(3)))
        if _dot(m, m) > 0.5 and all(_dot(h, m) > 0.05 for h in hs):
            sw = max(sb._solid_half_width(c["ptype"]) for c in conns)
            top = max(z for c in conns for poly in COLLISION_PROFILES.get(c["ptype"], []) for _, z in poly)
            mp = (-m[1], m[0], 0.0)
            planes = [((0, 0, -1.0), 200.0), ((0, 0, 1.0), top), (_mul(m, -1.0), sw + 100.0),
                      (mp, sw * 2.0), (_mul(mp, -1.0), sw * 2.0)]
            for c, h in zip(conns, hs):
                planes.append((h, -sb._crossing_back(c, conns)))
            s = _convex_shape(planes, o)
            if s is not None:
                shapes.append(s)
    return _set(sm, shapes)


# ----------------------------------------------------------------------------- rooms
ROOM_SIDES = {"Junction": 32, "Shaft": 16}      # facets of the modelled round wall


def _sector_planes(a0, a1, r_in, r_out, z0, z1):
    """Wall block between two angles: flat inner face on the chord (like the modelled wall)."""
    p0 = (math.cos(a0), math.sin(a0), 0.0)
    p1 = (math.cos(a1), math.sin(a1), 0.0)
    mid = _unit(_add(p0, p1))
    half = (a1 - a0) / 2.0
    inner = r_in * math.cos(half)
    outer = r_out / math.cos(half)
    n0 = (math.sin(a0), -math.cos(a0), 0.0)         # side planes through the centre
    n1 = (-math.sin(a1), math.cos(a1), 0.0)
    return [(_mul(mid, -1.0), -inner), (mid, outer), (n0, 0.0), (n1, 0.0),
            ((0, 0, -1.0), -z0), ((0, 0, 1.0), z1)]


def room_collision(sm, conns, ntype):
    """Junction / shaft: floor disc, ceiling disc, the round wall in facets (opened where a
    passage leaves), and each passage's blocks through the doorway out to where it starts."""
    import sewer_builder as sb
    cfg = sb.NODE_TYPES[ntype]
    rin, rout = cfg["inner_radius"], cfg["outer_radius"]
    n = ROOM_SIDES.get(ntype, 32)
    jit = math.radians(sb.SHELL_JITTER_DEG)
    o = _opts()
    shapes = []

    def add(planes):
        s = _convex_shape(planes, o)
        if s is not None:
            shapes.append(s)

    def disc(r, z0, z1, rot=0.0, sides=32):
        planes = [((0, 0, -1.0), -z0), ((0, 0, 1.0), z1)]
        for i in range(sides):
            a = rot + (i + 0.5) * 2 * math.pi / sides
            nn = (math.cos(a), math.sin(a), 0.0)
            planes.append((nn, r * math.cos(math.pi / sides)))
        add(planes)

    disc(rin, -100.0, 0.0)                                    # the floor (modelled base)
    # the whole ceiling as one octagon reaching past the outside of the wall
    disc(rout / math.cos(math.pi / 8), cfg["room_top_z"], cfg["room_top_z"] + 95.0, 0.0, 8)
    arms = []
    for c in conns:
        if c["ptype"] not in COLLISION_PROFILES:
            continue
        h = _unit((c["h"].x, c["h"].y, 0.0))
        ey = (-h[1], h[0], 0.0)
        wv = sb._void_half_width(c["ptype"])
        top = max(z for poly in COLLISION_PROFILES[c["ptype"]] for _, z in poly)
        top += (rout - rin) * abs(math.tan(math.radians(c["pitch"])))
        arms.append((c, h, ey, wv, top))
    z0, z1 = -295.0, cfg["room_top_z"]
    for i in range(n):
        a0 = jit + i * 2 * math.pi / n
        a1 = a0 + 2 * math.pi / n
        base = _sector_planes(a0, a1, rin, rout, z0, z1)
        hits = []
        for (c, h, ey, wv, top) in arms:
            mid = (math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0.0)
            if _dot(mid, h) <= 0:
                continue
            corners = [(math.cos(a) * r, math.sin(a) * r) for a in (a0, a1) for r in (rin * 0.9, rout * 1.1)]
            ys = [x * ey[0] + y * ey[1] for x, y in corners]
            if min(ys) < wv and max(ys) > -wv:
                hits.append((c, h, ey, wv, top))
        if not hits:
            add(base)
            continue
        def add_clear(planes, me):
            """add, kept out of every OTHER doorway through this facet (both sides of it)."""
            parts = [planes]
            for (c2, h2, ey2, wv2, top2) in hits:
                if c2 is me:
                    continue
                nxt = []
                d2 = _unit((c2["d"].x, c2["d"].y, c2["d"].z))
                ez2 = _cross(d2, ey2)
                o2 = _mul(h2, rin)
                for pl in parts:
                    nxt.append(pl + [(_mul(ey2, -1.0), -wv2)])                  # p.ey2 >= wv2
                    nxt.append(pl + [(ey2, -wv2)])                              # p.ey2 <= -wv2
                    nxt.append(pl + [(ey2, wv2), (_mul(ey2, -1.0), wv2), ((0, 0, -1.0), -top2)])  # above it
                    # and inside its band, wherever that passage itself is solid: the wall above its
                    # arch (its springer / roof shapes). Without this, two doorways close together
                    # left a hole above the lower one, up to the taller one's full height
                    for poly2 in COLLISION_PROFILES[c2["ptype"]]:
                        if min(z for _, z in poly2) < 1.0:
                            continue                                    # walls beside it: covered above
                        pr = _prism_planes(poly2, o2, d2, ey2, ez2, -100000.0, 100000.0)[:-2]
                        nxt.append(pl + pr)
                parts = nxt
            for pl in parts:
                add(pl)
        for (c, h, ey, wv, top) in hits:
            # the facet beside the doorway on either side, and the wall above it
            add_clear(base + [(ey, -wv)], c)
            add_clear(base + [(_mul(ey, -1.0), -wv)], c)
            add_clear(base + [(ey, wv), (_mul(ey, -1.0), wv), ((0, 0, -1.0), -top)], c)
    mitres = sb._crossing_mitres(conns) if len(conns) > 1 else {}
    # same floor path as the room's mesh: level until clear of the neighbours, then sloping to the
    # passage joint (sb._crossing_levels)
    levels = sb._crossing_levels(conns, rin) if len(conns) > 1 else [rin] * len(conns)
    for k, c in enumerate(conns):
        if c["ptype"] not in COLLISION_PROFILES:
            continue
        h = _unit((c["h"].x, c["h"].y, 0.0))
        ey = (-h[1], h[0], 0.0)
        d = _unit((c["d"].x, c["d"].y, c["d"].z))
        ez = _cross(d, ey)
        start = _mul(h, rin)
        joint = _add(start, _mul(d, c["lead"]))
        lv = min(levels[k], rin + c["lead"] * 0.95)
        if lv > rin + 1.0 and abs(c["pitch"]) >= sb.GEOM_LEVEL_EPS_DEG:
            e0 = _mul(h, lv)
            d2 = _unit(_sub(joint, e0))
            runs = [(start, h, _cross(h, ey), -rin, lv - rin),
                    (e0, d2, _cross(d2, ey), 0.0, math.sqrt(_dot(_sub(joint, e0), _sub(joint, e0))))]
        else:
            runs = [(start, d, ez, -rin, c["lead"])]
        for poly, (o_, ex_, ez_, x0_, x1_) in [(p_, r_) for p_ in COLLISION_PROFILES[c["ptype"]] for r_ in runs]:
            planes = _prism_planes(poly, o_, ex_, ey, ez_, x0_, x1_)
            side = sum(y for y, _ in poly) / len(poly)
            side_dir = _mul(ey, 1.0 if side > 0 else -1.0)
            for (a, b2), (C, D, ref) in mitres.items():
                if k not in (a, b2):
                    continue
                other = conns[b2 if k == a else a]
                if not (abs(side) < 1.0 or _dot(side_dir, (other["h"].x, other["h"].y, 0.0)) > 0):
                    continue
                dx, dy = D[0] - C[0], D[1] - C[1]
                n2 = _unit((-dy, dx, 0.0))
                sref = _dot(n2, (ref[0] - C[0], ref[1] - C[1], 0.0))
                mine = (sref >= 0) == (k == a)
                n3 = n2 if not mine else _mul(n2, -1.0)
                planes.append((n3, _dot(n3, (C[0], C[1], 0.0))))
            # in a room the doorways sit close together: a side block must also stay out of every
            # neighbouring passage's walkable interior (it used to block a narrow neighbour's doorway)
            alts = [[]]                   # alternative extra cuts (each makes its own block)
            if abs(side) >= 1.0:
                for j, cj in enumerate(conns):
                    if j == k or cj["ptype"] not in COLLISION_PROFILES:
                        continue
                    hj = _unit((cj["h"].x, cj["h"].y, 0.0))
                    if _dot(hj, h) < math.cos(math.radians(150.0)) or _dot(side_dir, hj) <= 0:
                        continue                  # straight across, or this block faces away from it
                    eyj = (-hj[1], hj[0], 0.0)
                    sg = 1.0 if _dot(h, eyj) > 0 else -1.0
                    wj = sb._void_half_width(cj["ptype"])
                    if max(z for _, z in poly) <= 0.5:
                        # a FLOOR block (walkway): only keep it out of the neighbour's channel - out of
                        # its whole interior, where two walkways overlap neither floor was left
                        # (you fell through)
                        wj = sb.PASSAGE_TYPES[cj["ptype"]].get("water_half_width", wj)
                        alts = [a_ + [(_mul(eyj, -sg), -wj)] for a_ in alts]
                    else:
                        # a wall / roof block: beside the neighbour's interior, or above its ceiling
                        # (cut away at every height, a lower neighbour left a hole in a taller roof)
                        topj = max(z for _, z in sb.PASSAGE_TYPES[cj["ptype"]]["void_profile"])
                        topj += (rout - rin) * abs(math.tan(math.radians(cj["pitch"]))) + 2.0
                        exs = [[(_mul(eyj, -sg), -wj)], [((0.0, 0.0, -1.0), -topj)]]
                        # ...or inside that passage's own solid above its arch (its springer / roof
                        # shapes): near its side its vault is much lower than its crown
                        dj = _unit((cj["d"].x, cj["d"].y, cj["d"].z))
                        ezj = _cross(dj, eyj)
                        for pj in COLLISION_PROFILES[cj["ptype"]]:
                            if min(z for _, z in pj) >= 1.0:
                                exs.append(_prism_planes(pj, _mul(hj, rin), dj, eyj, ezj, -100000.0, 100000.0)[:-2])
                        alts = [a_ + ex_ for a_ in alts for ex_ in exs]
            # one piece per wall facet it passes, starting exactly on that facet's inner face
            for i in range(n):
                a0 = jit + i * 2 * math.pi / n
                a1 = a0 + 2 * math.pi / n
                mid = _unit(((math.cos(a0) + math.cos(a1)) / 2, (math.sin(a0) + math.sin(a1)) / 2, 0.0))
                if _dot(mid, h) <= 0.0:
                    continue
                inner = rin * math.cos(math.pi / n)
                sec = [((math.sin(a0), -math.cos(a0), 0.0), 0.0), ((-math.sin(a1), math.cos(a1), 0.0), 0.0),
                       (_mul(mid, -1.0), -inner)]
                for a_ in alts:
                    add(planes + sec + a_)
    return _set(sm, shapes)


def apply_level(only=None, save=True):
    """Recomputes the box collision of every crossing / room in the open level (no rebuild)."""
    import os
    import sewer_builder as sb
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    nodes = [a for a in eas.get_all_level_actors() if sb._is_node(a)]
    edges, per = sb._gather(nodes, [])
    log = []
    for n in nodes:
        nt = sb._node_type(n)
        if sb._is_end(nt) or (only is not None and n.get_path_name() not in only):
            continue
        comp = n.get_component_by_class(unreal.StaticMeshComponent)
        sm = comp.get_editor_property("static_mesh") if comp else None
        if not sm:
            continue
        conns = sb._local_conns(n, per.get(n.get_path_name(), []))
        k = crossing_collision(sm, conns, sb.CROSSING_HUB) if sb._is_crossing(nt) else room_collision(sm, conns, nt)
        elems = len(sm.get_editor_property("body_setup").get_editor_property("agg_geom").get_editor_property("convex_elems"))
        log.append("%s: %d blocks (%d in asset)" % (n.get_actor_label(), k, elems))
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    if save:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "collision_out.txt"), "w").write("\n".join(log))
    return log


_LATER = {"handle": None, "t": 0.0}


def apply_level_later(only=None, delay=4.0):
    """Unreal finishes building freshly baked meshes a moment later and that throws away
    collision set right after the bake: apply it a few seconds later, then save the level."""
    import time
    if _LATER["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(_LATER["handle"])
    _LATER["t"] = time.time() + delay

    _LATER["runs"] = 2   # the first set after a fresh bake doesn't stick; the second one does

    def tick(dt):
        if time.time() < _LATER["t"]:
            return
        _LATER["runs"] -= 1
        if _LATER["runs"] <= 0:
            unreal.unregister_slate_post_tick_callback(_LATER["handle"])
            _LATER["handle"] = None
        else:
            _LATER["t"] = time.time() + delay
        try:
            apply_level(only=only, save=_LATER["runs"] <= 0)
        except Exception as e:  # noqa
            unreal.log_warning("Sewer: box collision failed (%s)" % e)
    _LATER["handle"] = unreal.register_slate_post_tick_callback(tick)
