"""
Sewer Builder for Unreal Engine 5  (Editor Python + Geometry Script)
====================================================================

What it does when you run build():
  1. Finds every BP_SewerNode in the level and reads its connections.
  2. Validates them (allowed passage types, max slope, min angle, run length).
  3. For every node, generates a mesh with Geometry Script:
        node shell  + passage solids (clipped to the wall)
        - passage voids (level stub mitred into the sloped lead-in)
        + floor base with the channels cut into it
     and bakes it to a static mesh asset (Nanite + complex-as-simple collision),
     which is assigned to the node's own Static Mesh component.
  4. Spawns one "SewerNetwork_GENERATED" actor holding HISMs for every
     passage type and every node water disc, and fills them with instances.

Node types (NodeType on BP_SewerNode): Junction, Shaft (round rooms), Crossing (no room:
passages meet at the pivot - L, T, Y, X, 5-way...), End (capped dead end).
Close-angle passages are handled: node geometry keeps going until neighbouring passages
have separated, so instanced passages never overlap.

Nothing runs at game time. Re-run build() whenever you move or reconnect nodes.
Test scene: sewer_test_layout.make() then build().

Usage (Output Log, Python mode):
    import importlib, sewer_builder; importlib.reload(sewer_builder); sewer_builder.build()
First-time check of passage profiles:
    sewer_builder.preview_profiles()

Requires plugins: Python Editor Script Plugin, Geometry Script (+ Editor Scripting Utilities on older 5.x).
All units are centimetres, in Unreal space (Z up, X forward).
"""

import math
import os
import unreal

# =============================================================================
# CONFIG - edit to match your project
# =============================================================================

GENERATED_FOLDER = "/Game/Sewers/Generated"
NODE_CLASS_NAME = "BP_SewerNode_C"           # Blueprint class name + "_C"
NODE_TYPE_PROPERTY = "NodeType"              # Name variable on BP_SewerNode
NETWORK_LABEL = "SewerNetwork_GENERATED"
# World Partition: split the passages/water/end walls into one actor per NETWORK_CELL square so the
# level streams them like any other actor (one big actor would always be loaded). Each actor holds
# one instanced component per piece type. Off = the old single actor split into CULL_CELL_SIZE cells.
NETWORK_SPLIT = False
NETWORK_CELL = 12800.0          # cm (128 m)
NETWORK_FOLDER = "Sewers/Network"

NODE_MATERIAL = "/Game/Sewers/Meshes/v2/sewer1_003"     # material for generated caps
PASSAGE_UV_TOL = 0.6       # cm: cut faces within this of a passage profile edge get that face's UVs/material
WATER_MATERIAL = "/Game/Sewers/Materials/MI_SewerWaterV2_Opaque"  # top of the water (opaque, one-sided); sewer_water_underside.py adds the view from below

# Node types. Radii/heights measured from your FBX (pivot at walkway/floor = Z 0).
NODE_TYPES = {
    "Junction": {
        "shell_mesh": "/Game/Sewers/Meshes/v2/Junctiontest",   # was /Game/Sewers/Meshes/SM_Junction  # the cylinder shell ONLY (no base)
        "inner_radius": 600.0,
        "outer_radius": 701.0,
        "room_floor_z": -200.0,   # inside bottom of the shell
        "room_top_z": 590.0,      # inside ceiling of the shell
        "base_mesh": "/Game/Sewers/Meshes/v2/JunctionBasetest",   # was /Game/Sewers/Meshes/SM_JunctionBase  # floor, placed as-is (never cut)
        "allowed_passages": {"P12", "P20"},
    },
    "Shaft": {
        "shell_mesh": "/Game/Sewers/Meshes/v2/Shafttest",       # was /Game/Sewers/Meshes/SM_Shaft
        "inner_radius": 300.0,
        "outer_radius": 403.0,
        "room_floor_z": -200.0,
        "room_top_z": 590.0,
        "base_mesh": "/Game/Sewers/Meshes/v2/ShaftBasetest",       # was /Game/Sewers/Meshes/SM_ShaftBase
        "allowed_passages": {"P12", "P20"},  # P20 fits (one, or straight through); crowded combos show pillar warnings
    },
    # Crossing: no room. Passages meet at the pivot; their outer blocks are joined and
    # their interiors cut out, giving groin-vaulted crossings, T's, L's, Y's, 5-ways...
    "Crossing": {
        "is_crossing": True,
        "allowed_passages": {"P12", "P20"},
    },
    # Dead end: no room, the passage runs to the node's pivot and gets a cap wall.
    "End": {
        "is_end": True,
        "allowed_passages": {"P12", "P20"},
    },
}

CAP_THICKNESS = 40.0      # thickness of the generated end-cap wall

# Passage types. Profiles are (Y, Z) in the passage's cross-section, CCW.
#   void_profile  = the walkable interior incl. channel (taken from your mesh)
#   solid_profile = anything enclosing the outer shell (a box is fine, only seen from outside)
PASSAGE_TYPES = {
    "P12": {
        "property": "Passage12To",            # Array<BP_SewerNode> variable on the node
        "mesh": "/Game/Sewers/Meshes/v2/Passage12test",          # was v2/Passage12
        "end_mesh": "/Game/Sewers/Meshes/v2/Passage12endtest",  # was v2/SM_SewerEnd12;
        "end_front": "max",                    # which X side of the end mesh faces into the passage ("min" for the old pieces);   # modelled dead-end wall (None = generated)
        "water_mesh": "/Game/Sewers/Meshes/v2/Water12test",     # modelled water strip (None = generated)
        "water_half_width": 60.0,             # channel half width (lead strips / hub water)
        "segment_length": 400.0,
        "half_width": 220.0,                  # outer half width (for min-angle checks)
        "crown": 370.0,                       # interior ceiling height above walkway
        # v2: walkways both sides, channel centred (-60..60, 100 deep)
        "void_profile": [(-120, 0), (-60, 0), (-60, -100), (60, -100), (60, 0), (120, 0), (120, 250),
                         (104, 310), (60, 354), (0, 370), (-60, 354), (-104, 310), (-120, 250)],
        "solid_profile": [(-220, -200), (220, -200), (220, 474), (-220, 474)],
    },
    "P20": {
        "property": "Passage20To",
        "mesh": "/Game/Sewers/Meshes/v2/Passage20test",          # was v2/Passage20
        "end_mesh": "/Game/Sewers/Meshes/v2/Passage20endtest",  # was v2/SM_SewerEnd20;
        "end_front": "max",                    # which X side of the end mesh faces into the passage ("min" for the old pieces);   # modelled dead-end wall (None = generated)
        "water_mesh": "/Game/Sewers/Meshes/v2/Water20test",
        "water_half_width": 100.0,
        "segment_length": 400.0,
        "half_width": 300.0,
        "crown": 550.0,
        "void_profile": [(-200, 0), (-100, 0), (-100, -100), (100, -100), (100, 0), (200, 0),
                         (200, 350), (173, 450), (100, 523), (0, 550), (-100, 523),
                         (-173, 450), (-200, 350)],
        "solid_profile": [(-300, -200), (300, -200), (300, 654), (-300, 654)],
    },
}

PASSAGE_UVS = {   # interior faces as UNREAL sees them (read from the imported meshes):
    # ((y0,z0),(y1,z1), material slot, uv at x=0 (p0,p1), uv at x=400 (p0,p1))
    "P12": [
        ((-120.0, 0.0), (-60.0, 0.0), 1, ((1.0000, 1.0000), (0.7500, 1.0000)), ((1.0000, -0.0000), (0.7500, -0.0000))),
        ((-60.0, 0.0), (-60.0, -100.0), 0, ((1.0000, 0.7200), (1.0000, 0.8900)), ((0.0000, 0.7200), (-0.0000, 0.8900))),
        ((-60.0, -100.0), (60.0, -100.0), 1, ((0.7500, 1.0000), (0.2500, 1.0000)), ((0.7500, 0.0000), (0.2500, -0.0000))),
        ((60.0, -100.0), (60.0, 0.0), 0, ((1.0000, 0.8900), (1.0000, 0.7200)), ((-0.0000, 0.8900), (-0.0000, 0.7200))),
        ((60.0, 0.0), (120.0, 0.0), 1, ((0.7500, 1.0000), (1.0000, 1.0000)), ((0.7500, -0.0000), (1.0000, -0.0000))),
        ((120.0, 0.0), (120.0, 250.0), 0, ((1.0000, 1.0000), (1.0000, 0.5800)), ((-0.0000, 1.0000), (-0.0000, 0.5800))),
        ((120.0, 250.0), (104.0, 310.0), 0, ((1.2500, 0.5400), (1.2500, 0.4200)), ((0.2500, 0.5400), (0.2500, 0.4200))),
        ((104.0, 310.0), (60.0, 354.0), 0, ((1.0000, 0.6600), (1.0000, 0.5299)), ((-0.0000, 0.6600), (0.0000, 0.5299))),
        ((60.0, 354.0), (0.0, 370.0), 0, ((1.0000, 0.1400), (1.0000, -0.0000)), ((-0.0000, 0.1400), (-0.0000, -0.0000))),
        ((0.0, 370.0), (-60.0, 354.0), 0, ((1.0000, 0.0000), (1.0000, 0.1400)), ((-0.0000, 0.0000), (-0.0000, 0.1400))),
        ((-60.0, 354.0), (-104.0, 310.0), 0, ((1.0000, 0.5299), (1.0000, 0.6600)), ((-0.0000, 0.5299), (-0.0000, 0.6600))),
        ((-104.0, 310.0), (-120.0, 250.0), 0, ((1.2500, 0.4200), (1.2500, 0.5400)), ((0.2500, 0.4200), (0.2500, 0.5400))),
        ((-120.0, 250.0), (-120.0, 0.0), 0, ((1.0000, 0.5800), (1.0000, 1.0000)), ((-0.0000, 0.5800), (-0.0000, 1.0000))),
    ],
    "P20": [
        ((-200.0, 0.0), (-100.0, 0.0), 1, ((0.0000, -0.0000), (0.2500, -0.0000)), ((0.0000, 1.0000), (0.2500, 1.0000))),
        ((-100.0, 0.0), (-100.0, -100.0), 0, ((0.0000, 0.8100), (0.0000, 0.9500)), ((1.0000, 0.8100), (1.0000, 0.9500))),
        ((-100.0, -100.0), (100.0, -100.0), 2, ((0.7500, 1.0000), (0.2500, 1.0000)), ((0.7500, 0.0000), (0.2500, -0.0000))),
        ((100.0, -100.0), (100.0, 0.0), 0, ((-0.0000, 0.9500), (-0.0000, 0.8100)), ((1.0000, 0.9500), (1.0000, 0.8100))),
        ((100.0, 0.0), (200.0, 0.0), 1, ((0.7500, 1.0000), (1.0000, 1.0000)), ((0.7500, -0.0000), (1.0000, -0.0000))),
        ((200.0, 0.0), (200.0, 350.0), 0, ((1.0000, 1.0000), (1.0000, 0.4100)), ((-0.0000, 1.0000), (-0.0000, 0.4100))),
        ((200.0, 350.0), (173.0, 450.0), 0, ((1.0000, 0.4100), (1.0000, 0.2300)), ((-0.0000, 0.4100), (-0.0000, 0.2300))),
        ((173.0, 450.0), (100.0, 523.0), 0, ((1.0000, 0.2300), (1.0000, 0.1200)), ((-0.0000, 0.2300), (-0.0000, 0.1200))),
        ((100.0, 523.0), (0.0, 550.0), 0, ((1.0000, 0.1201), (1.0000, 0.0000)), ((-0.0000, 0.1201), (0.0000, 0.0000))),
        ((0.0, 550.0), (-100.0, 523.0), 0, ((1.0000, -0.0000), (1.0000, 0.1201)), ((-0.0000, -0.0000), (-0.0000, 0.1201))),
        ((-100.0, 523.0), (-173.0, 450.0), 0, ((1.0000, 0.1200), (1.0000, 0.2300)), ((-0.0000, 0.1200), (-0.0000, 0.2300))),
        ((-173.0, 450.0), (-200.0, 350.0), 0, ((1.0000, 0.2300), (1.0000, 0.4100)), ((0.0000, 0.2300), (-0.0000, 0.4100))),
        ((-200.0, 350.0), (-200.0, 0.0), 0, ((1.0000, 0.4100), (1.0000, 1.0000)), ((0.0000, 0.4100), (-0.0000, 1.0000))),
    ],
}

PASSAGE_MESH_POINTS_PLUS_X = True  # False if your passage mesh runs along -X from its pivot

WATER_Z = -45.0           # water surface height (matches Water12test/Water20test)
WATER_TUCK = 30.0
WATER_OVERLAP = 1.5        # cm: each water piece runs this far under the next. The edges match exactly, but
                           # the GPU rounds two separately placed pieces differently, which leaves hairline
                           # cracks; the shading is world-space and identical where pieces meet, so the
                           # overlap itself can't be seen
WATER_BASE_SPEED = 1.0     # (old flow material) flow speed on level passages
WATER_SPEED_PER_DEG = 0.25 # (old flow material) extra speed per degree of slope
# flow by travel time: every water point knows how many seconds the water took to get there,
# and the material shows the ripple texture at (now - that time): one continuous pattern that
# runs faster where the water is fast. Speeds in cm/s.
FLOW_SPEED_LEVEL = 60.0    # level passage
FLOW_SPEED_PER_DEG = 12.0  # extra per degree of slope (15 deg: 240 cm/s)
FLOW_SPEED_NODE = 30.0     # slows to this where it meets a crossing / room (the crossing water moves at it too)
FLOW_EASE = 600.0          # cm over which it speeds up after a node and slows before the next
FLOW_CUSTOM = 7            # per-instance floats: distance + travel time at local x=0 and far end, speed at both ends, mode
WATER_MATERIAL_FALLBACK = None         # node water starts this far under the base so there's no gap at its edge
STUB_MARGIN = 50.0        # node mesh extends this far past the outer wall
PILLAR_MIN = 50.0         # min wall left between two openings (warning only)
LINTEL_MIN = 20.0         # min wall left above an opening
MAX_SLOPE_DEG = 20.0      # global slope cap
MIN_RUN = 100.0           # min passage length between two node meshes
LEVEL_EPS_DEG = 0.5       # below this a connection counts as level
GEOM_LEVEL_EPS_DEG = 0.01  # geometry: any real slope is followed (a 0.4 deg arm built level ended up to 4 cm off the tunnel piece)
VOID_OVERSHOOT = 300.0    # how far void pieces overlap before the mitre trims them
SOLID_BACK = 200.0        # passage solid starts this far inside the bend (clipped away)
BUILD_COLLARS = True       # debug switch
SEPARATION_MARGIN = 60.0   # node geometry runs this far past where neighbouring passages separate
MAX_LEAD = 3000.0          # cap for very shallow angles (warns)
CROSSING_MARGIN = 80.0     # crossing geometry extends at least widest half-width + this
CROSSING_HUB = 260.0       # crossings are level within this radius; slopes start outside it
CROSSING_VOID_INSET = 2.0
BACK_FLOOR = 0.3           # corner-fill floor sits this hair above the walkway (avoids coplanar cuts)  # crossing interiors reach back to (their half-width - this) behind the centre
OUTER_MIN_KINK_DEG = 0.5   # outer corners: turns sharper than straight-through by more than this
OPPOSITE_DEG = 170.0       # passages closer than this to straight-through don't reach back
PROFILE_JITTER = 0.002     # per-connection scale jitter on crossing profiles (avoids coplanar booleans)
COLLAR_OVERLAP = 8.0       # collars start this far inside the wall's outer face
SHELL_JITTER_DEG = 1.37    # rotates the round wall slightly to avoid degenerate boolean cuts
SWEEP_MITER_LIMIT = 4.0    # lets the swept cutter keep full size through the bend
MITRE_OVERLAP = 2.0       # level and sloped voids overlap by this much at the bend
VOID_PAST_END = 150.0     # void runs this far past the node mesh end (slopes tilt the end face)
UV_BOX_SIZE = 200.0       # box-projection UV tile size (use triplanar material anyway)
SPLIT_NORMAL_ANGLE = 30.0
BASE_OVERHANG = 2.0        # cm the floor base overlaps the doorway floors
RECOMPUTE_NORMALS = False  # False: wall keeps its own normals, cut surfaces inherit the cutters' normals
SUBTRACT_BASE = False      # rooms: cut the floor base out of the wall (its corners notch every wall facet;
                           # the base sits 1 mm high and overhangs a hair, so leaving both is clean)
SIMPLE_COLLISION = True    # generated meshes get simple collision (slabs behind their surfaces), project default trace
ENABLE_NANITE = False      # applied to every mesh the sewer uses (generated + your passage/end meshes)
CULL_CELL_SIZE = 2000.0    # passages/water/end walls are split into instanced components per cell this
                           # size, so normal (per-component) frustum + occlusion culling can drop them
CIRCLE_STEPS = 64

# =============================================================================
# Geometry Script helpers
# =============================================================================

V = unreal.Vector
IDENT = unreal.Transform()
BASE = unreal.GeometryScriptPrimitiveOriginMode.BASE
UNION = unreal.GeometryScriptBooleanOperation.UNION
SUBTRACT = unreal.GeometryScriptBooleanOperation.SUBTRACT
PRIM = unreal.GeometryScriptPrimitiveOptions()
BOOL_OPTS = unreal.GeometryScriptMeshBooleanOptions()

# profile (Y,Z) -> passage frame: profile X->passage Y, profile Y->passage Z, extrude Z->passage X
_PROFILE_ROT = unreal.MathLibrary.make_rotation_from_axes(V(0, 1, 0), V(0, 0, 1), V(1, 0, 0))

_GS_CACHE = {}


_GS_LIBRARIES = (
    "MeshBasicEditFunctions", "MeshPrimitiveFunctions", "MeshBooleanFunctions", "MeshModelingFunctions",
    "MeshNormalsFunctions", "MeshUVFunctions", "MeshQueryFunctions", "MeshTransformFunctions",
    "MeshMaterialFunctions", "MeshSelectionFunctions", "MeshSimplifyFunctions", "MeshRepairFunctions",
    "MeshDeformFunctions", "MeshSpatial", "MeshDecompositionFunctions", "MeshVertexColorFunctions",
    "MeshPolygroupFunctions", "MeshSubdivideFunctions", "CollisionFunctions", "MeshBakeFunctions",
    "StaticMeshFunctions", "MeshComparisonFunctions", "ContainmentFunctions", "PolyPathFunctions",
    "SceneUtilityFunctions", "VolumeFunctions", "VectorMathFunctions", "TransformFunctions",
    "MeshGeodesicFunctions", "MeshVoxelFunctions", "MeshSamplingFunctions", "MeshRemeshFunctions",
)


def _load_gs_libraries():
    for lib in _GS_LIBRARIES:
        for mod in ("GeometryScriptingCore", "GeometryScriptingEditor"):
            try:
                unreal.load_class(None, "/Script/%s.GeometryScriptLibrary_%s" % (mod, lib))
            except Exception:
                pass


def gs(name):
    """Find a Geometry Script function regardless of which library class exposes it."""
    if name in _GS_CACHE:
        return _GS_CACHE[name]
    for attempt in range(2):
        for attr in dir(unreal):
            if attr.startswith("GeometryScript"):
                fn = getattr(getattr(unreal, attr), name, None)
                if callable(fn):
                    _GS_CACHE[name] = fn
                    return fn
        if attempt == 0:
            _load_gs_libraries()   # some projects only expose a library to Python once its class is loaded
    # the same functions are also exposed as methods of the types they work on (call them unbound)
    for owner in ("DynamicMesh", "StaticMesh", "DynamicMeshComponent", "DynamicMeshActor"):
        fn = getattr(getattr(unreal, owner, None), name, None)
        if callable(fn):
            _GS_CACHE[name] = fn
            return fn
    raise RuntimeError("Geometry Script function '%s' not found - is the Geometry Script plugin enabled?" % name)


def _pick(result, cls):
    if isinstance(result, cls):
        return result
    if isinstance(result, (tuple, list)):
        for r in result:
            if isinstance(r, cls):
                return r
    return None


def _floats(result):
    if isinstance(result, (int, float)):
        return [float(result)]
    if isinstance(result, (tuple, list)):
        return [float(r) for r in result if isinstance(r, (int, float)) and not isinstance(r, bool)]
    return []


def _new_mesh():
    return unreal.DynamicMesh()


def _boolean(target, tool, op):
    gs("apply_mesh_boolean")(target, IDENT, tool, IDENT, op, BOOL_OPTS)


def _append_prism(target, profile, start, direction, length):
    """Extrude a (Y,Z) profile from `start` along `direction` for `length`."""
    pts = [unreal.Vector2D(float(y), float(z)) for (y, z) in profile]
    t0 = unreal.Transform(rotation=_PROFILE_ROT)
    t1 = unreal.Transform(location=start, rotation=unreal.MathLibrary.make_rot_from_x(direction))
    xf = unreal.MathLibrary.compose_transforms(t0, t1)
    gs("append_simple_extrude_polygon")(target, PRIM, xf, pts, float(length), 0, True, BASE)


_ORIENTED = {}


def _oriented(profile):
    """Make sure the extruded prism is not inside-out (booleans need correct winding)."""
    key = tuple(profile)
    if key in _ORIENTED:
        return _ORIENTED[key]
    out = list(profile)
    try:
        test = _new_mesh()
        _append_prism(test, out, V(0, 0, 0), V(1, 0, 0), 100.0)
        nums = _floats(gs("get_mesh_volume_area")(test))
        if nums and nums[-1] < 0:
            out = list(reversed(out))
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: could not verify profile winding (%s); using as written." % e)
    _ORIENTED[key] = out
    return out


def _subtract_halfspace(target, point, normal):
    """Remove everything on the `normal` side of the plane through `point`."""
    tool = _new_mesh()
    xf = unreal.Transform(location=point, rotation=unreal.MathLibrary.make_rot_from_z(normal))
    gs("append_box")(tool, PRIM, xf, 100000.0, 100000.0, 100000.0, 0, 0, 0, BASE)
    _boolean(target, tool, SUBTRACT)


def _set_nanite(sm):
    """Make a static mesh match ENABLE_NANITE (only touches it if it differs)."""
    if sm is None:
        return
    try:
        ns = sm.get_editor_property("nanite_settings")
        if bool(ns.get_editor_property("enabled")) != ENABLE_NANITE:
            ns.set_editor_property("enabled", ENABLE_NANITE)
            sm.set_editor_property("nanite_settings", ns)
            unreal.EditorAssetLibrary.save_asset(sm.get_path_name().split(".")[0], only_if_is_dirty=False)
            unreal.log("Sewer: Nanite %s on %s" % ("enabled" if ENABLE_NANITE else "disabled", sm.get_name()))
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: could not set Nanite on %s (%s)" % (sm.get_name(), e))


def _bake(mesh, asset_path, material_path, simple=True):
    """Write the dynamic mesh into a static mesh asset (create or update)."""
    eal = unreal.EditorAssetLibrary
    slot_list = None
    if isinstance(material_path, (list, tuple)):
        # the asset's material slots must be exactly this list (index = material ID); stale
        # slots from an earlier bake would otherwise keep catching triangles
        slot_list = [unreal.StaticMaterial(material_interface=eal.load_asset(p) if p else None,
                                           material_slot_name=unreal.Name(p.split(".")[-1] if p else "None"))
                     for p in material_path]
    if eal.does_asset_exist(asset_path):
        sm = eal.load_asset(asset_path)
        if slot_list is not None:
            sm.set_editor_property("static_materials", slot_list)
        gs("copy_mesh_to_static_mesh")(mesh, sm, unreal.GeometryScriptCopyMeshToAssetOptions(),
                                       unreal.GeometryScriptMeshWriteLOD())
    else:
        opts = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
        for prop, val in (("enable_nanite", ENABLE_NANITE), ("enable_collision", True)):
            try:
                opts.set_editor_property(prop, val)
            except Exception:
                pass
        sm = _pick(gs("create_new_static_mesh_asset_from_mesh")(mesh, asset_path, opts), unreal.StaticMesh)
        if sm is None:
            raise RuntimeError("Could not create asset " + asset_path)
    if slot_list is not None:
        if len(sm.get_editor_property("static_materials")) != len(slot_list):
            sm.set_editor_property("static_materials", slot_list)
            gs("copy_mesh_to_static_mesh")(mesh, sm, unreal.GeometryScriptCopyMeshToAssetOptions(),
                                           unreal.GeometryScriptMeshWriteLOD())
        for i, s in enumerate(slot_list):
            m = s.get_editor_property("material_interface")
            if m:
                sm.set_material(i, m)
    elif material_path:
        mat = eal.load_asset(material_path)
        if mat:
            sm.set_material(0, mat)
        else:
            unreal.log_warning("Sewer: material not found: " + material_path)
    try:
        bs = sm.get_editor_property("body_setup")
        if bs:
            bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: could not set collision on %s (%s)" % (asset_path, e))
    eal.save_asset(asset_path, only_if_is_dirty=False)
    _set_nanite(sm)
    if SIMPLE_COLLISION and simple and "DEBUG" not in asset_path:
        try:
            import sewer_simplecol
            sewer_simplecol.apply_to(sm)       # thin slabs behind every surface: walkable inside
        except Exception as e:  # noqa
            unreal.log_warning("Sewer: simple collision failed on %s (%s)" % (asset_path, e))
    return sm


def _normals(mesh):
    try:
        so = unreal.GeometryScriptSplitNormalsOptions()
        so.set_editor_property("split_by_opening_angle", True)
        so.set_editor_property("opening_angle_deg", SPLIT_NORMAL_ANGLE)
        gs("compute_split_normals")(mesh, so, unreal.GeometryScriptCalculateNormalsOptions())
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: normals step skipped (%s)" % e)


def _finish_mesh(mesh, normals=None):
    if normals is None:
        normals = RECOMPUTE_NORMALS
    if not normals:
        _finish_uvs(mesh)
        return
    try:
        so = unreal.GeometryScriptSplitNormalsOptions()
        so.set_editor_property("split_by_opening_angle", True)
        so.set_editor_property("opening_angle_deg", SPLIT_NORMAL_ANGLE)
        gs("compute_split_normals")(mesh, so, unreal.GeometryScriptCalculateNormalsOptions())
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: normals step skipped (%s)" % e)
    _finish_uvs(mesh)


def _finish_uvs(mesh):
    try:
        box = unreal.Transform(scale=V(UV_BOX_SIZE, UV_BOX_SIZE, UV_BOX_SIZE))
        try:
            fn = gs("set_mesh_u_vs_from_box_projection")   # UE 5.4+ Python name
        except RuntimeError:
            fn = gs("set_mesh_uvs_from_box_projection")
        fn(mesh, 0, box, unreal.GeometryScriptMeshSelection(), 2)
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: UV step skipped (%s)" % e)


# -----------------------------------------------------------------------------
# Materials + UVs of generated node meshes
#   every node mesh gets its own material list (_SLOTS); the shell/base keep their own
#   materials and UVs, cut surfaces get exactly the passage's materials and UVs
# -----------------------------------------------------------------------------

_SLOTS = []   # material asset paths of the node mesh being built (index = material ID)


def _slot(path):
    if path not in _SLOTS:
        _SLOTS.append(path)
    return _SLOTS.index(path)


def _asset_materials(sm):
    out = []
    for m in sm.get_editor_property("static_materials"):
        mi = m.get_editor_property("material_interface")
        out.append(mi.get_path_name() if mi else None)
    return out


def _remap_to_slots(mesh, sm):
    """Mesh copied from static mesh `sm`: move its material IDs (sm's slots) into _SLOTS."""
    gs("enable_material_i_ds")(mesh)
    mats = _asset_materials(sm)
    for i in range(len(mats)):
        gs("remap_material_i_ds")(mesh, i, 1000 + i)
    for i, p in enumerate(mats):
        if not p or p.startswith("/Engine/"):     # unassigned / default grid: use the node material
            p = NODE_MATERIAL
        gs("remap_material_i_ds")(mesh, 1000 + i, _slot(p))


def _set_all_material(mesh, mid):
    gs("enable_material_i_ds")(mesh)
    for t in range(gs("get_num_triangle_i_ds")(mesh)):
        gs("set_triangle_material_id")(mesh, t, mid, True)


def _passage_slots(ptype):
    sm = unreal.EditorAssetLibrary.load_asset(PASSAGE_TYPES[ptype]["mesh"])
    return [_slot(p) for p in _asset_materials(sm)] if sm else [0, 0, 0]


def _tri_positions(mesh, t):
    r = gs("get_triangle_positions")(mesh, t)
    if isinstance(r, tuple):
        vs = [x for x in r if isinstance(x, unreal.Vector)]
        ok = [x for x in r if isinstance(x, bool)]
        return (vs if (not ok or ok[0]) and len(vs) == 3 else None)
    return None


def _seg_param(p, a, b):
    """(distance from p to segment ab, param t along it), 2D."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    ll = dx * dx + dy * dy
    t = 0.0 if ll < 1e-9 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / ll))
    qx, qy = a[0] + dx * t, a[1] + dy * t
    return math.hypot(p[0] - qx, p[1] - qy), t


def _uv_on_edge(e, t, x):
    (a0, b0), (a4, b4) = e[3], e[4]
    u0 = a0[0] + (b0[0] - a0[0]) * t
    v0 = a0[1] + (b0[1] - a0[1]) * t
    u4 = a4[0] + (b4[0] - a4[0]) * t
    v4 = a4[1] + (b4[1] - a4[1]) * t
    k = x / 400.0
    # the table holds the UVs exactly as Unreal has them (read from the imported meshes)
    return unreal.Vector2D(u0 + (u4 - u0) * k, v0 + (v4 - v0) * k)


_UV_TABLES = {}


def _solve3(A, y):
    """Least squares for 3 unknowns via normal equations (no numpy in every UE install)."""
    M = [[sum(r[i] * r[j] for r in A) for j in range(3)] for i in range(3)]
    b = [sum(r[i] * v for r, v in zip(A, y)) for i in range(3)]

    def det(m):
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    d = det(M)
    if abs(d) < 1e-9:
        return None
    out = []
    for k in range(3):
        mk = [row[:] for row in M]
        for i in range(3):
            mk[i][k] = b[i]
        out.append(det(mk) / d)
    return out


def _uv_table(ptype):
    """The passage mesh's interior UVs per void-profile edge, read from the asset itself (so
    UV changes in Blender carry over after a re-import). Falls back to PASSAGE_UVS."""
    if ptype in _UV_TABLES:
        return _UV_TABLES[ptype]
    table = PASSAGE_UVS.get(ptype)
    try:
        sm = unreal.EditorAssetLibrary.load_asset(PASSAGE_TYPES[ptype]["mesh"])
        m = _new_mesh()
        gs("copy_mesh_from_static_mesh")(sm, m, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                         unreal.GeometryScriptMeshReadLOD())
        tris = []
        n_sets = gs("get_num_uv_sets")(m)
        for t in range(gs("get_num_triangle_i_ds")(m)):
            vs = _tri_positions(m, t)
            if not vs:
                continue
            uv = gs("get_triangle_u_vs")(m, 0, t)
            uvs = [u for u in uv if isinstance(u, unreal.Vector2D)] if isinstance(uv, tuple) else []
            uv1 = gs("get_triangle_u_vs")(m, 1, t) if n_sets > 1 else None
            uv1 = [u for u in uv1 if isinstance(u, unreal.Vector2D)] if isinstance(uv1, tuple) else []
            mid = gs("get_triangle_material_id")(m, t)
            mid = mid[0] if isinstance(mid, tuple) else mid
            if len(uvs) == 3:
                tris.append((vs, uvs, int(mid), uv1))
        prof = PASSAGE_TYPES[ptype]["void_profile"]
        rows = []
        for i in range(len(prof)):
            a, b = prof[i], prof[(i + 1) % len(prof)]
            A, U, Vv, mids, cells = [], [], [], [], []
            for vs, uvs, mid, uv1 in tris:
                ds = [_seg_param((p.y, p.z), a, b) for p in vs]
                if all(d < 1.5 for d, _ in ds) and max(p.x for p in vs) - min(p.x for p in vs) > 1.0:
                    for (d, tt), p, uv in zip(ds, vs, uvs):
                        A.append((1.0, tt, p.x))
                        U.append(uv.x)
                        Vv.append(uv.y)
                    mids.append(mid)
                    cells += [(u.x, u.y) for u in uv1]
            cu, cv = (_solve3(A, U), _solve3(A, Vv)) if A else (None, None)
            if cu is None or cv is None:
                raise RuntimeError("no faces for profile edge %s-%s" % (a, b))
            f = lambda tt, x: (cu[0] + cu[1] * tt + cu[2] * x, cv[0] + cv[1] * tt + cv[2] * x)  # noqa
            cell = (sum(c[0] for c in cells) / len(cells), sum(c[1] for c in cells) / len(cells)) if cells else None
            rows.append((a, b, max(set(mids), key=mids.count), (f(0, 0), f(1, 0)), (f(0, 400), f(1, 400)), cell))
        table = rows
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: reading %s UVs from the mesh failed (%s); using the stored table" % (ptype, e))
    _UV_TABLES[ptype] = table
    return table


def _edge_cell(e):
    return e[5] if len(e) > 5 else None


def _wall_edge(table):
    """The side wall: vertical profile edge on the +Y side above the walkway."""
    cands = [e for e in table if abs(e[0][0] - e[1][0]) < 0.5 and min(e[0][1], e[1][1]) >= -0.5]
    return max(cands, key=lambda e: e[0][0]) if cands else table[0]


def _floor_edge(table):
    """The outer walkway: horizontal profile edge at walkway height furthest from the centre."""
    cands = [e for e in table if abs(e[0][1]) < 0.5 and abs(e[1][1]) < 0.5]
    return max(cands, key=lambda e: max(abs(e[0][0]), abs(e[1][0]))) if cands else table[0]


def _set_uv_triangle(m, uv_set, t, uvs):
    tri = unreal.GeometryScriptUVTriangle()
    tri.set_editor_property("uv0", unreal.Vector2D(*uvs[0]) if isinstance(uvs[0], tuple) else uvs[0])
    tri.set_editor_property("uv1", unreal.Vector2D(*uvs[1]) if isinstance(uvs[1], tuple) else uvs[1])
    tri.set_editor_property("uv2", unreal.Vector2D(*uvs[2]) if isinstance(uvs[2], tuple) else uvs[2])
    gs("set_mesh_triangle_u_vs")(m, uv_set, t, tri, True)


def _ensure_uv_sets(m, n=2):
    try:
        if gs("get_num_uv_sets")(m) < n:
            gs("set_num_uv_sets")(m, n)
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: could not add UV sets (%s)" % e)


def _outer_cell(ptype):
    """Atlas cell (UV1) for generated outside faces: the passage's wall cell."""
    table = _uv_table(ptype)
    return _edge_cell(_wall_edge(table)) if table else None


_OUTER = {}


def _hull2(pts):
    """Convex hull of (y, z) points, counter-clockwise (monotone chain)."""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for q in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 1e-6:
            lo.pop()
        lo.append(q)
    for q in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], q) <= 1e-6:
            hi.pop()
        hi.append(q)
    return lo[:-1] + hi[:-1]


def _outer_look(ptype):
    """How the passage piece looks from outside, read from the asset itself: its outer shell
    cross-section (convex hull of the piece, (y, z)) and the flat colour its outside is painted
    with (UV0, UV1, the piece's material index). Generated node meshes copy it so their outside
    looks exactly like the tunnels'. Falls back to the solid_profile box and box UVs."""
    if ptype in _OUTER:
        return _OUTER[ptype]
    cfg = PASSAGE_TYPES[ptype]
    res = {"profile": cfg["solid_profile"], "uv0": None, "uv1": None, "mid": 0}
    try:
        sm = unreal.EditorAssetLibrary.load_asset(cfg["mesh"])
        m = _new_mesh()
        gs("copy_mesh_from_static_mesh")(sm, m, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                         unreal.GeometryScriptMeshReadLOD())
        n_sets = gs("get_num_uv_sets")(m)
        pts, flats = [], {}
        for t in range(gs("get_num_triangle_i_ds")(m)):
            vs = _tri_positions(m, t)
            if not vs:
                continue
            pts += [(round(q.y, 1), round(q.z, 1)) for q in vs]
            uv = gs("get_triangle_u_vs")(m, 0, t)
            uvs = [u for u in uv if isinstance(u, unreal.Vector2D)] if isinstance(uv, tuple) else []
            if len(uvs) != 3 or max(abs(u.x - uvs[0].x) + abs(u.y - uvs[0].y) for u in uvs) > 1e-4:
                continue                                    # outside: one flat colour per face
            key = (round(uvs[0].x, 4), round(uvs[0].y, 4))
            uv1 = None
            if n_sets > 1:
                r1 = gs("get_triangle_u_vs")(m, 1, t)
                r1 = [u for u in r1 if isinstance(u, unreal.Vector2D)] if isinstance(r1, tuple) else []
                if r1:
                    uv1 = (r1[0].x, r1[0].y)
            mid = gs("get_triangle_material_id")(m, t)
            mid = mid[0] if isinstance(mid, tuple) else mid
            f = flats.setdefault(key, [0, (uvs[0].x, uvs[0].y), uv1, int(mid)])
            f[0] += 1
        hull = _hull2(pts)
        w_cfg = max(abs(y) for (y, z) in cfg["solid_profile"])
        if len(hull) >= 3 and max(abs(y) for (y, z) in hull) <= w_cfg + 1.0:
            res["profile"] = hull
        if flats:
            best = max(flats.values(), key=lambda f: f[0])
            res["uv0"], res["uv1"], res["mid"] = best[1], best[2], best[3]
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: reading the outside of %s failed (%s); box outside" % (ptype, e))
    cfg["outer_profile"] = res["profile"]
    _OUTER[ptype] = res
    return res


def _paint_outside(m, ptype):
    """Outside of a generated piece: the passage piece's own outside colour (UV0 + UV1 +
    material), or box UVs with the wall cell where that could not be read."""
    look = _outer_look(ptype)
    slots = _passage_slots(ptype)
    if look["uv0"] is None:
        _finish_uvs(m)
        _set_cell_all(m, _outer_cell(ptype))
        _set_all_material(m, slots[0])
        return
    _ensure_uv_sets(m)
    u0 = look["uv0"]
    u1 = look["uv1"] or u0
    for t in range(gs("get_num_triangle_i_ds")(m)):
        _set_uv_triangle(m, 0, t, [u0, u0, u0])
        _set_uv_triangle(m, 1, t, [u1, u1, u1])
    _set_all_material(m, slots[look["mid"]] if look["mid"] < len(slots) else slots[0])


def _set_cell_all(m, cell):
    """Give every triangle of m the same UV1 (atlas cell), for faces with no passage match."""
    if cell is None:
        return
    _ensure_uv_sets(m)
    for t in range(gs("get_num_triangle_i_ds")(m)):
        _set_uv_triangle(m, 1, t, [cell, cell, cell])


class _PathFrame(object):
    """(x, z) in a connection cutter's frame -> (distance along its path, height off the path).
    The path runs level to `level_at` (default `rin`), then straight to the passage joint (at
    rin + lead along the passage slope) and on along the slope. Distances are scaled on the middle
    stretch so the joint is exactly at rin + lead (the passage pieces' texture phase)."""

    def __init__(self, c, rin, level_at=None):
        p = math.radians(c["pitch"])
        self.rin, self.cp, self.sp = rin, math.cos(p), math.sin(p)
        lead = c["lead"]
        self.lv = rin if level_at is None else max(rin, min(level_at, rin + self.cp * lead - 1.0))
        self.ex, self.ez = rin + self.cp * lead, self.sp * lead          # the joint
        dx, dz = self.ex - self.lv, self.ez
        ch = math.hypot(dx, dz) or 1.0
        self.d1 = (dx / ch, dz / ch)
        self.k = (rin + lead - self.lv) / ch
        self.n1 = (1.0 + self.d1[0], self.d1[1])                          # mitre: slope starts
        self.n2 = (self.d1[0] + self.cp, self.d1[1] + self.sp)            # mitre: the joint

    def stretch(self, cx, cz):
        """The mapping of the stretch the point (cx, cz) is on."""
        if (cx - self.ex) * self.n2[0] + (cz - self.ez) * self.n2[1] > 0.0:
            rin, cp, sp = self.rin, self.cp, self.sp
            return lambda x, z: (rin + (x - rin) * cp + z * sp, -(x - rin) * sp + z * cp)
        if (cx - self.lv) * self.n1[0] + cz * self.n1[1] > 0.0:
            lv, d1, k = self.lv, self.d1, self.k
            return lambda x, z: (lv + ((x - lv) * d1[0] + z * d1[1]) * k, -(x - lv) * d1[1] + z * d1[0])
        return lambda x, z: (x, z)


def _path_frame(c, rin, level_at=None):
    return _PathFrame(c, rin, level_at)


def _frame_at(frame, cx, cz, x, z):
    """A vertex in the frame of the stretch the triangle centre (cx, cz) is on."""
    return frame.stretch(cx, cz)(x, z)


def _paint_passage_uvs(m, c, rin, s_start, scale=1.0, tol=PASSAGE_UV_TOL, level_at=None):
    """Give a swept cutter (canonical frame: path along +X, level up to `rin`, then bending
    in the X-Z plane by the connection's pitch) the passage mesh's UVs and materials, so
    every surface it cuts continues the passage's texturing (same tiling and phase)."""
    ptype = c["ptype"]
    table = _uv_table(ptype)
    if not table:
        return
    slots = _passage_slots(ptype)
    gs("enable_material_i_ds")(m)
    _ensure_uv_sets(m)
    wall_e, floor_e = _wall_edge(table), _floor_edge(table)
    wall_slot = slots[wall_e[2]] if wall_e[2] < len(slots) else slots[0]
    floor_slot = slots[floor_e[2]] if floor_e[2] < len(slots) else slots[0]
    # wall texture density for planar fallbacks (cap faces): V per cm of height, U per cm along
    (wy0, wz0), (wy1, wz1) = wall_e[0], wall_e[1]
    w_v0, w_v1 = wall_e[3][0][1], wall_e[3][1][1]
    w_dvdz = (w_v1 - w_v0) / (wz1 - wz0) if abs(wz1 - wz0) > 1e-6 else 0.0
    w_dudx = (wall_e[4][0][0] - wall_e[3][0][0]) / 400.0
    level = abs(c["pitch"]) < GEOM_LEVEL_EPS_DEG
    frame = None if level else _path_frame(c, rin, level_at)
    mirror = bool(c.get("mirror"))
    seg = PASSAGE_TYPES[ptype]["segment_length"]
    for t in range(gs("get_num_triangle_i_ds")(m)):
        vs = _tri_positions(m, t)
        if vs is None:
            continue
        cx = sum(q.x for q in vs) / 3.0
        cz = sum(q.z for q in vs) / 3.0
        loc = []
        for q in vs:
            if frame is not None:
                # the whole triangle in the frame of the stretch its centre is on (one stretch
                # per triangle, as the cutter's rings are mitred exactly there)
                s, z = _frame_at(frame, cx, cz, q.x, q.z)
            else:
                s, z = q.x, q.z
            y = -q.y if mirror else q.y
            x = (s_start - s) if mirror else (s - s_start)
            loc.append((x * 400.0 / seg, y / scale, z / scale if z < 0.0 else z))
        best = None
        for e in table:
            worst, ts = 0.0, []
            for (x, y, z) in loc:
                dist, tt = _seg_param((y, z), e[0], e[1])
                worst = max(worst, dist)
                ts.append(tt)
            if worst <= tol and (best is None or worst < best[0]):
                best = (worst, e, ts)
        if best:
            e, ts = best[1], best[2]
            uvs = [_uv_on_edge(e, tt, x) for tt, (x, y, z) in zip(ts, loc)]
            mid = slots[e[2]] if e[2] < len(slots) else wall_slot
            cell = _edge_cell(e)
        else:
            flat = max(z for (_, _, z) in loc) - min(z for (_, _, z) in loc) < 1.0 and loc[0][2] > -1.0
            if flat:   # channel-free floor (crossing corners): the walkway's mapping, extended across
                (fy0, _), (fy1, _) = floor_e[0], floor_e[1]
                span = (fy1 - fy0) if abs(fy1 - fy0) > 1e-6 else 1.0
                uvs = [_uv_on_edge(floor_e, (y - fy0) / span, x) for (x, y, z) in loc]
                mid, cell = floor_slot, _edge_cell(floor_e)
            else:      # end caps etc.: wall texture, planar on the cross-section
                uvs = [unreal.Vector2D(0.5 + y * w_dudx, w_v0 + (z - wz0) * w_dvdz) for (x, y, z) in loc]
                mid, cell = wall_slot, _edge_cell(wall_e)
        _set_uv_triangle(m, 0, t, uvs)
        if cell is not None:
            _set_uv_triangle(m, 1, t, [cell, cell, cell])
        gs("set_triangle_material_id")(m, t, mid, True)


def _safe(name):
    return "".join(c if c.isalnum() else "_" for c in name)


# =============================================================================
# Scene reading + validation
# =============================================================================

def _actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def _is_node(actor):
    return actor is not None and actor.get_class().get_name() == NODE_CLASS_NAME


def _node_type(node):
    return str(node.get_editor_property(NODE_TYPE_PROPERTY))


def _is_end(ntype):
    return NODE_TYPES[ntype].get("is_end", False)


def _is_crossing(ntype):
    return NODE_TYPES[ntype].get("is_crossing", False)


def _has_room(ntype):
    return not _is_end(ntype) and not _is_crossing(ntype)


def _solid_half_width(ptype):
    return max(abs(y) for (y, z) in PASSAGE_TYPES[ptype]["solid_profile"])


def _void_half_width(ptype):
    return max(abs(y) for (y, z) in PASSAGE_TYPES[ptype]["void_profile"])


def _radii(ntype):
    """(inner radius, minimum horizontal distance from bend to where the passage run starts)."""
    cfg = NODE_TYPES[ntype]
    if _is_end(ntype):
        return 0.0, 0.0
    if _is_crossing(ntype):
        widest = max(_solid_half_width(p) for p in PASSAGE_TYPES)
        return CROSSING_HUB, max(widest + CROSSING_MARGIN - CROSSING_HUB, 100.0)
    return cfg["inner_radius"], cfg["outer_radius"] + STUB_MARGIN - cfg["inner_radius"]


def _separation(angle_deg, w_self, w_other):
    """Horizontal distance from the node centre along one passage until a neighbouring
    passage (angle_deg away, both treated as bands from the centre) no longer overlaps it."""
    a = math.radians(angle_deg)
    if angle_deg >= 90.0:
        return max(w_self, w_other)
    if angle_deg < 0.5:
        return float("inf")
    return (w_other + w_self * math.cos(a)) / math.sin(a)


def _max_slope(ptype, ntype):
    if not _has_room(ntype):
        return MAX_SLOPE_DEG
    crown = PASSAGE_TYPES[ptype]["crown"]
    room = NODE_TYPES[ntype]["room_top_z"] - LINTEL_MIN
    if crown >= room:
        return 0.0
    return min(MAX_SLOPE_DEG, math.degrees(math.acos(crown / room)))


def _gather(nodes, warnings):
    """Returns (edges, per_node_connections)."""
    seen, edges, raw = set(), [], []
    per_node = {n.get_path_name(): [] for n in nodes}

    for a in nodes:
        ta = _node_type(a)
        if ta not in NODE_TYPES:
            warnings.append("%s: unknown NodeType '%s'" % (a.get_actor_label(), ta))
            continue
        rot = a.get_actor_rotation()
        if abs(rot.pitch) > 0.1 or abs(rot.roll) > 0.1:
            warnings.append("%s: node is pitched/rolled; only yaw is supported" % a.get_actor_label())

        for ptype, pcfg in PASSAGE_TYPES.items():
            try:
                targets = a.get_editor_property(pcfg["property"]) or []
            except Exception:
                warnings.append("BP_SewerNode has no variable '%s'" % pcfg["property"])
                continue
            for b in targets:
                if not _is_node(b) or b == a:
                    continue
                key = (ptype,) + tuple(sorted([a.get_path_name(), b.get_path_name()]))
                if key in seen:
                    continue
                seen.add(key)
                tb = _node_type(b)
                if tb not in NODE_TYPES:
                    continue
                label = "%s -> %s (%s)" % (a.get_actor_label(), b.get_actor_label(), ptype)

                if ptype not in NODE_TYPES[ta]["allowed_passages"] or ptype not in NODE_TYPES[tb]["allowed_passages"]:
                    warnings.append("%s: passage type not allowed on %s/%s - skipped" % (label, ta, tb))
                    continue

                rin_a, _ = _radii(ta)
                rin_b, _ = _radii(tb)
                pa, pb = a.get_actor_location(), b.get_actor_location()
                h = V(pb.x - pa.x, pb.y - pa.y, 0.0)
                if h.length() < 1.0:
                    warnings.append("%s: nodes are stacked vertically - skipped" % label)
                    continue
                h = h.normal()
                bend_a = pa + h * rin_a
                bend_b = pb - h * rin_b
                d = (bend_b - bend_a).normal()
                pitch = math.degrees(math.asin(max(-1.0, min(1.0, d.z))))
                limit = min(_max_slope(ptype, ta), _max_slope(ptype, tb))
                if abs(pitch) > limit + 1e-3:
                    warnings.append("%s: slope %.1f deg exceeds max %.1f deg - skipped" % (label, pitch, limit))
                    continue
                raw.append({"a": a, "b": b, "ta": ta, "tb": tb, "ptype": ptype, "label": label,
                            "h": h, "d": d, "pitch": pitch, "bend_a": bend_a, "bend_b": bend_b})

    # pass 2: how far each node's own geometry must reach along each connection
    # (at least past its wall, and until neighbouring passages have separated)
    ends = {}  # (edge index, 0|1) -> horizontal lead
    by_node = {}
    for k, e in enumerate(raw):
        by_node.setdefault(e["a"].get_path_name(), []).append((k, 0, e["h"]))
        by_node.setdefault(e["b"].get_path_name(), []).append((k, 1, e["h"] * -1.0))
    for path, items in by_node.items():
        for (k, side, hdir) in items:
            e = raw[k]
            ntype = e["ta"] if side == 0 else e["tb"]
            node = e["a"] if side == 0 else e["b"]
            rin, lead_h = _radii(ntype)
            if not _is_end(ntype):
                w_self = _solid_half_width(e["ptype"])
                for (k2, side2, hdir2) in items:
                    if (k2, side2) == (k, side):
                        continue
                    cosang = max(-1.0, min(1.0, hdir.dot(hdir2)))
                    ang = math.degrees(math.acos(cosang))
                    sep = _separation(ang, w_self, _solid_half_width(raw[k2]["ptype"])) + SEPARATION_MARGIN
                    if sep - rin > lead_h:
                        lead_h = sep - rin
                if lead_h > MAX_LEAD:
                    warnings.append("%s: two passages leave at a very shallow angle; merged section capped at %.0f cm"
                                    % (node.get_actor_label(), MAX_LEAD))
                    lead_h = MAX_LEAD
            ends[(k, side)] = lead_h

    for k, e in enumerate(raw):
        d, pitch, h = e["d"], e["pitch"], e["h"]
        cos_p = max(0.1, math.cos(math.radians(pitch)))
        lead_a = ends[(k, 0)] / cos_p
        lead_b = ends[(k, 1)] / cos_p
        run_start = e["bend_a"] + d * lead_a
        run_end = e["bend_b"] - d * lead_b
        run_len = (run_end - run_start).dot(d)
        if run_len < MIN_RUN:
            warnings.append("%s: nodes too close (run %.0f cm) - no passage segments placed" % (e["label"], run_len))
        edges.append({"ptype": e["ptype"], "start": run_start, "dir": d, "length": run_len, "label": e["label"],
                      "a": e["a"].get_path_name(), "b": e["b"].get_path_name(), "pitch": pitch,
                      "end": run_end, "cap_a": _is_end(e["ta"]), "cap_b": _is_end(e["tb"]),
                      "bend_a": e["bend_a"], "lead_a": lead_a, "lead_b": lead_b,
                      "cross_a": _is_crossing(e["ta"]), "cross_b": _is_crossing(e["tb"]),
                      "pa": e["a"].get_actor_location(), "pb": e["b"].get_actor_location()})
        eid = len(edges) - 1
        per_node[e["a"].get_path_name()].append({"ptype": e["ptype"], "h": h, "d": d, "lead": lead_a, "pitch": pitch,
                                                 "eid": eid})
        # B looks back along the passage, so asymmetric profiles must be mirrored there
        per_node[e["b"].get_path_name()].append({"ptype": e["ptype"], "h": h * -1.0, "d": d * -1.0,
                                                 "lead": lead_b, "pitch": -pitch, "mirror": True, "eid": eid})
    return edges, per_node


def _check_angles(node, conns, warnings):
    if _is_end(_node_type(node)):
        if len(conns) != 1:
            warnings.append("%s: End node has %d connections (expected 1)" % (node.get_actor_label(), len(conns)))
        return
    if not _has_room(_node_type(node)):
        return
    cfg = NODE_TYPES[_node_type(node)]
    rin = cfg["inner_radius"]
    # the pillar that matters is the wall left INSIDE the room between two interiors
    # (outside, the passages' outer blocks merge anyway)
    items = sorted((math.degrees(math.atan2(c["h"].y, c["h"].x)) % 360.0,
                    _void_half_width(c["ptype"])) for c in conns)
    if len(items) < 2:
        return
    for i in range(len(items)):
        ya, wa = items[i]
        yb, wb = items[(i + 1) % len(items)]
        gap = (yb - ya) % 360.0
        need = 0.0
        for w in (wa, wb):
            s = (w + PILLAR_MIN / 2.0) / rin
            need += 90.0 if s >= 1.0 else math.degrees(math.asin(s))
        if gap < need:
            warnings.append("%s: openings %.0f deg apart, need about %.0f deg for a %.0f cm pillar"
                            % (node.get_actor_label(), gap, need, PILLAR_MIN))


# =============================================================================
# Node mesh generation
# =============================================================================

def _profile(c, kind, scale=1.0):
    prof = PASSAGE_TYPES[c["ptype"]][kind]
    if c.get("mirror"):
        prof = [(-y, z) for (y, z) in reversed(prof)]
    if scale != 1.0:
        prof = [(y * scale, z * scale) for (y, z) in prof]
    return _oriented(prof)


def _connection_voids(c, rin, back=10.0, scale=1.0, clip=None, level_at=None):
    """Void (interior) cutter for one connection, in node-local space: ONE swept shape that
    starts `back` behind the node centre, runs level to the bend at `rin`, then follows the
    passage slope (mitred at the bend by the sweep itself - no booleans between pieces,
    which left hairline cracks on shallow slopes)."""
    prof = _profile_raw(c, "void_profile", scale)
    L = c["lead"] + VOID_PAST_END
    lead = c["lead"]
    p = math.radians(c["pitch"])
    level = abs(c["pitch"]) < GEOM_LEVEL_EPS_DEG
    # an extra ring exactly where the passage pieces start, so the cutter can be brought back
    # to the exact passage size there (no ridge at the joint)
    if level:
        path = [V(-back, 0, 0), V(rin + lead, 0, 0), V(rin + L, 0, 0)]
    else:
        cp, sp = math.cos(p), math.sin(p)
        lv = rin if level_at is None else max(rin, min(level_at, rin + cp * lead - 1.0))
        path = [V(-back, 0, 0), V(lv, 0, 0), V(rin + cp * lead, 0, sp * lead), V(rin + cp * L, 0, sp * L)]
    swept = _sweep(prof, path)
    if clip:
        # node-local vertical plane (point, normal) -> this cutter's frame (+X along c["h"]);
        # cut before painting so the cut face gets the wall texture (it shows where a taller
        # passage turns into a lower one)
        (pt, nm), hx, hy = clip, c["h"].x, c["h"].y
        _subtract_halfspace(swept, V(pt.x * hx + pt.y * hy, -pt.x * hy + pt.y * hx, 0.0),
                            V(nm.x * hx + nm.y * hy, -nm.x * hy + nm.y * hx, 0.0))
    _paint_passage_uvs(swept, c, rin, rin + c["lead"], scale, level_at=None if level else lv)
    if scale != 1.0:
        _unjitter_tail(swept, c, rin, rin + lead, scale)
    out = _new_mesh()
    gs("append_mesh")(out, swept, unreal.Transform(rotation=unreal.MathLibrary.make_rot_from_x(c["h"])))
    _normals(out)
    return [out]


def _unjitter_tail(m, c, rin, s_start, scale):
    """Crossing cutters are scaled a hair (PROFILE_JITTER) so arms never share faces in the hub.
    Undo that on the rings from the passage start onwards, so the cutter matches the passage
    exactly where the instanced pieces attach (the scale fades out over the arm)."""
    p = math.radians(c["pitch"])
    level = abs(c["pitch"]) < GEOM_LEVEL_EPS_DEG
    cp, sp = math.cos(p), math.sin(p)
    for vid in range(gs("get_num_vertex_i_ds")(m)):
        r = gs("get_vertex_position")(m, vid)
        q = r[0] if isinstance(r, tuple) else r
        if not isinstance(q, unreal.Vector):
            continue
        if level:
            along, z = q.x, q.z
        else:
            rx, rz = q.x - rin, q.z
            along, z = rin + rx * cp + rz * sp, -rx * sp + rz * cp
        if along < s_start - 0.5:
            continue
        y = q.y / scale
        if z < 0.0:
            z = z / scale
        if level:
            new = V(along, y, z)
        else:
            a = along - rin
            new = V(rin + a * cp - z * sp, y, a * sp + z * cp)
        gs("set_vertex_position")(m, vid, new, True)


def _sweep(profile, path):
    """Sweep a (Y, Z) profile along a path lying in the local X-Z plane (+X forward).
    UE's sweep maps polygon (u, v) to (-Z, +Y) in that frame."""
    def build(prof):
        m = _new_mesh()
        poly = [unreal.Vector2D(float(-z), float(y)) for (y, z) in prof]
        gs("append_simple_swept_polygon")(m, PRIM, IDENT, poly, path, False, True, 1.0, 1.0, 0.0, SWEEP_MITER_LIMIT)
        return m
    m = build(profile)
    try:
        nums = _floats(gs("get_mesh_volume_area")(m))
        if nums and nums[-1] < 0:
            m = build(list(reversed(profile)))
    except Exception:
        pass
    return m


def _profile_raw(c, kind, scale=1.0):
    prof = PASSAGE_TYPES[c["ptype"]][kind]
    if c.get("mirror"):
        prof = [(-y, z) for (y, z) in reversed(prof)]
    if scale != 1.0:
        if kind == "void_profile":
            # jitter sideways and in the channel only: vaults of the same passage type must
            # share one crown height, or they cross in long paper-thin slivers at the top
            prof = [(y * scale, z * scale if z < 0.0 else z) for (y, z) in prof]
        else:
            prof = [(y * scale, z * scale) for (y, z) in prof]
    return prof


def _disjoint(pieces):
    """Make overlapping solid pieces disjoint (each minus the ones before it), so that after
    cutting the voids no interior surface exists twice."""
    out = []
    for k, p in enumerate(pieces):
        q = _new_mesh()
        gs("append_mesh")(q, p, IDENT)
        for prev in pieces[:k]:
            _boolean(q, prev, SUBTRACT)
        out.append(q)
    return out


def _angle_between(c1, c2):
    return math.degrees(math.acos(max(-1.0, min(1.0, c1["h"].dot(c2["h"])))))


def _crossing_back(c, conns):
    """How far a crossing interior reaches back behind the centre so corners fill in
    (L / T shapes) without carving niches into a neighbour's wall."""
    t = CROSSING_VOID_INSET
    for o in conns:
        if o is c:
            continue
        ang = _angle_between(c, o)
        if ang >= OPPOSITE_DEG:
            return CROSSING_VOID_INSET   # a straight-through partner continues the space
        if ang >= 90.0:
            # keep the whole reached-back cross-section (not just its centre) inside o's interior
            a = math.radians(ang)
            room = _void_half_width(o["ptype"]) - CROSSING_VOID_INSET - _void_half_width(c["ptype"]) * abs(math.cos(a))
            t = max(t, room / math.sin(a))
    return min(t, _void_half_width(c["ptype"]) * 3.0)


def _outer_corners(conns):
    """Neighbouring arms more than 180 deg apart (not straight through): the outside of a turn.
    Returns [(i, j, corner)] - corner = where i's left wall line meets j's right wall line
    (node-local plan coords), i.e. how far the open space reaches behind the centre there."""
    out = []
    n = len(conns)
    if n < 2:
        return out
    order = sorted(range(n), key=lambda k: math.atan2(conns[k]["h"].y, conns[k]["h"].x))
    for ii in range(n):
        i, j = order[ii], order[(ii + 1) % n]
        if i == j:
            continue
        hi = (conns[i]["h"].x, conns[i]["h"].y)
        hj = (conns[j]["h"].x, conns[j]["h"].y)
        li, lj = math.hypot(*hi), math.hypot(*hj)
        hi, hj = (hi[0] / li, hi[1] / li), (hj[0] / lj, hj[1] / lj)
        gap = (math.atan2(hj[1], hj[0]) - math.atan2(hi[1], hi[0])) % (2 * math.pi)
        # every turn counts, also a slight kink in an almost straight run (171 deg at SL_231 was
        # skipped and left a thin wedge of wall standing behind the centre on its outside)
        if gap <= math.pi + math.radians(OUTER_MIN_KINK_DEG) or gap >= math.radians(355.0):
            continue
        ni, nj = (-hi[1], hi[0]), (-hj[1], hj[0])
        wi, wj = _void_half_width(conns[i]["ptype"]), _void_half_width(conns[j]["ptype"])
        p0 = (ni[0] * wi, ni[1] * wi)
        q0 = (-nj[0] * wj, -nj[1] * wj)
        den = hi[0] * hj[1] - hi[1] * hj[0]
        if abs(den) < 1e-6:
            continue
        t = ((q0[0] - p0[0]) * hj[1] - (q0[1] - p0[1]) * hj[0]) / den
        corner = (p0[0] + hi[0] * t, p0[1] + hi[1] * t)
        if math.hypot(*corner) > 4.0 * max(wi, wj):
            continue
        out.append((i, j, corner))
    return out


def _clip_poly(poly, n, d):
    """Keep the part of a (y, z) polygon where n.(y, z) >= d (Sutherland-Hodgman)."""
    out = []
    k = len(poly)
    for i in range(k):
        a, b = poly[i], poly[(i + 1) % k]
        fa = n[0] * a[0] + n[1] * a[1] - d
        fb = n[0] * b[0] + n[1] * b[1] - d
        if fa >= 0:
            out.append(a)
        if (fa >= 0) != (fb >= 0):
            t = fa / (fa - fb)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


LEVEL_PAST_SHARED = 10.0   # cm: a sloping arm stays level this far past the floor it shares with a neighbour


def _crossing_levels(conns, hub):
    """Where each arm's floor starts to slope (distance from the centre). Normally `hub`, but an
    arm whose floor still overlaps a neighbour's there (the inner corner of two arms) stays level
    until it is clear of it: two floors sloping different ways over the same ground left a step
    of a few cm along the edge of one of them. The slope then runs a little steeper to the same
    joint with the passage, so nothing else moves."""
    out = []
    mitres = _crossing_mitres(conns)
    outer = _outer_mitres(conns)
    for k, c in enumerate(conns):
        R = hub
        if abs(c["pitch"]) >= GEOM_LEVEL_EPS_DEG:
            hk = (c["h"].x, c["h"].y)
            wk = _void_half_width(c["ptype"]) * (1.0 + PROFILE_JITTER * k)
            for j, o in enumerate(conns):
                if j == k:
                    continue
                hj = (o["h"].x, o["h"].y)
                wj = _void_half_width(o["ptype"]) * (1.0 + PROFILE_JITTER * j)
                big = 5000.0
                poly = [(-big, -big), (big, -big), (big, big), (-big, big)]
                for (h, w) in ((hk, wk), (hj, wj)):       # both interiors, in front of their backs
                    nl = (-h[1], h[0])
                    poly = _clip_poly(poly, nl, -w)
                    poly = _clip_poly(poly, (-nl[0], -nl[1]), -w)
                    poly = _clip_poly(poly, h, -CROSSING_VOID_INSET)
                if len(poly) >= 3:
                    R = max(R, max(q[0] * hk[0] + q[1] * hk[1] for q in poly) + LEVEL_PAST_SHARED)
            # stay level until past the corners this arm shares with its neighbours (the mitre
            # lines' wall and channel corners): a slope starting before them left the arm's floor
            # a few cm under the crossing floor between the corners (a step along the seam)
            for (a, b), (C, D, _ref) in mitres.items():
                if k in (a, b):
                    for P in (C, D):
                        R = max(R, P[0] * hk[0] + P[1] * hk[1] + LEVEL_PAST_SHARED)
            for (i, j, C, D, _si, _sj) in outer:
                if k in (i, j):
                    for P in (C, D):
                        R = max(R, P[0] * hk[0] + P[1] * hk[1] + LEVEL_PAST_SHARED)
            R = min(R, hub + math.cos(math.radians(c["pitch"])) * c["lead"] * 0.95)   # keep a slope
        out.append(R)
    return out


OUTER_FILL_FLOOR = 0.0


def _beyond_surface(c, k, side, hub):
    """Cutter: everything on one side (+1 = its left) of passage c's interior surface (walls and
    vault, above the walkway), along its whole axis through the node, node-local."""
    jit = 1.0 + PROFILE_JITTER * k
    prof = _profile_raw(c, "void_profile", jit)
    wv = max(abs(y) for (y, z) in prof)
    big = 5000.0
    # the surface on that side: wall from the walkway edge up, then the vault to the crown
    surf = [q for q in prof if q[0] * side >= -0.01 and q[1] >= -0.01 and (q[1] > 0.5 or abs(q[0]) >= wv - 0.5)]
    surf = sorted(set(surf), key=lambda q: (q[1], -abs(q[0])))
    if abs(surf[-1][0]) > 0.01:
        surf.append((0.0, max(q[1] for q in prof)))
    poly = surf + [(0.0, big), (side * big, big), (side * big, -1.0), (surf[0][0], -1.0)]
    # keep it a simple polygon going round one way
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
               for i in range(len(poly)))
    if area < 0:
        poly.reverse()
    sw = _sweep(poly, [V(-big, 0, 0), V(big, 0, 0)])
    # it lies exactly on that passage's wall and vault, and wherever the trim leaves its own
    # faces behind they must look like that wall (unpainted, they showed as a smeared strip
    # up the corner). Level frame: the cutter itself is level.
    flat = dict(c)
    flat["pitch"] = 0.0
    _paint_passage_uvs(sw, flat, hub, hub + c["lead"], jit, tol=1.6)
    out = _new_mesh()
    gs("append_mesh")(out, sw, unreal.Transform(rotation=unreal.MathLibrary.make_rot_from_x(c["h"])))
    _normals(out)
    return out


def _beyond_channel(c, k, side, hub):
    """Cutter: everything beyond passage c's channel wall on one side (+1 = its left), for the
    channel depth, along its whole axis, node-local - painted as that channel wall (a plain
    plane cut left an untextured face on it)."""
    jit = 1.0 + PROFILE_JITTER * k
    w = PASSAGE_TYPES[c["ptype"]].get("water_half_width", 0.0) * jit
    big = 5000.0
    bot = -100.0 * jit
    poly = [(side * w, bot - 10.0), (side * w, bot), (side * w, 0.0), (side * w, 5.0),
            (side * big, 5.0), (side * big, bot - 10.0)]
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
               for i in range(len(poly)))
    if area < 0:
        poly.reverse()
    sw = _sweep(poly, [V(-big, 0, 0), V(big, 0, 0)])
    flat = dict(c)
    flat["pitch"] = 0.0
    _paint_passage_uvs(sw, flat, hub, hub + c["lead"], jit, tol=1.6)
    out = _new_mesh()
    gs("append_mesh")(out, sw, unreal.Transform(rotation=unreal.MathLibrary.make_rot_from_x(c["h"])))
    _normals(out)
    return out


def _outer_corner_voids(conns, hub):
    """Open up the outside corner of every turn inside a crossing: each of the two arms reaches
    back behind the centre (its own interior, without the channel, on the corner's half only)
    as far as the corner, up to the lower of the two walls, and is trimmed at the other arm's
    wall line - so the two outer walls meet in a clean corner, with no wedge left standing and
    no niche cut into either wall."""
    voids = []
    for i, j, corner in _outer_corners(conns):
        for k, o in ((i, j), (j, i)):
            c, other = conns[k], conns[o]
            h = (c["h"].x, c["h"].y)
            nl = (-h[1], h[0])
            back = -(corner[0] * h[0] + corner[1] * h[1]) + 2.0
            if back <= CROSSING_VOID_INSET + 1.0:
                continue
            side = 1.0 if corner[0] * nl[0] + corner[1] * nl[1] > 0 else -1.0
            jit = 1.0 + PROFILE_JITTER * k
            # the arm's own interior shape (walls AND vault, so no wedge is left in the ceiling
            # either), without the channel, on the corner's half only
            # floor exactly at walkway level: a hair above left a 3 mm ledge you could see
            prof = _clip_poly(_profile_raw(c, "void_profile", jit), (0.0, 1.0), OUTER_FILL_FLOOR)
            prof = _clip_poly(prof, (side, 0.0), -1.0)
            if len(prof) < 3:
                continue
            v = _sweep(prof, [V(-back, 0, 0), V(hub * 0.5, 0, 0)])
            _paint_passage_uvs(v, c, hub, hub + c["lead"], jit, tol=1.6)
            out = _new_mesh()
            gs("append_mesh")(out, v, unreal.Transform(rotation=unreal.MathLibrary.make_rot_from_x(c["h"])))
            # trim at the other arm's wall line (its wall that faces the corner)
            ho = (other["h"].x, other["h"].y)
            no = (-ho[1], ho[0])
            so = 1.0 if corner[0] * no[0] + corner[1] * no[1] > 0 else -1.0
            # the other arm's wall where it really is (its cutter is scaled by its own jitter): a
            # trim at the plain width left a thin V-shaped slit up the corner
            wo = _void_half_width(other["ptype"]) * (1.0 + PROFILE_JITTER * o)
            # trim at the other arm's real surface - its wall AND its vault (a vertical cut at the
            # wall line left a slit widening up the corner where the vault curves in)
            _boolean(out, _beyond_surface(other, o, so, hub), SUBTRACT)
            _normals(out)
            voids.append(out)
            # the channel too: each channel starts square at the centre, which left a point of
            # walkway sticking into the water at the outside corner. Run it back to where the two
            # channels' outer edges meet, trimmed at the other channel's edge.
            ck = PASSAGE_TYPES[c["ptype"]].get("water_half_width", 0.0)
            co = PASSAGE_TYPES[other["ptype"]].get("water_half_width", 0.0) * (1.0 + PROFILE_JITTER * o)
            ck *= jit
            if ck <= 0 or co <= 0:
                continue
            den = h[0] * ho[1] - h[1] * ho[0]
            if abs(den) < 1e-6:
                continue
            p0 = (nl[0] * side * ck, nl[1] * side * ck)
            q0 = (no[0] * so * co, no[1] * so * co)
            t = ((q0[0] - p0[0]) * ho[1] - (q0[1] - p0[1]) * ho[0]) / den
            qc = (p0[0] + h[0] * t, p0[1] + h[1] * t)                 # the channels' outer corner
            cback = -(qc[0] * h[0] + qc[1] * h[1]) + 2.0
            if cback <= CROSSING_VOID_INSET + 1.0:
                continue
            chan = [(-ck, -100.0 * jit), (ck, -100.0 * jit), (ck, 1.0), (-ck, 1.0)]
            chan = _clip_poly(chan, (side, 0.0), -1.0)
            cv = _sweep(chan, [V(-cback, 0, 0), V(hub * 0.5, 0, 0)])
            _paint_passage_uvs(cv, c, hub, hub + c["lead"], jit, tol=1.6)
            out = _new_mesh()
            gs("append_mesh")(out, cv, unreal.Transform(rotation=unreal.MathLibrary.make_rot_from_x(c["h"])))
            _boolean(out, _beyond_channel(other, o, so, hub), SUBTRACT)
            _normals(out)
            voids.append(out)
    return voids


def _local_conns(node, conns_world):
    xf = node.get_actor_transform()
    conns = []
    for c in conns_world:
        cc = dict(c)
        cc["h"] = unreal.MathLibrary.inverse_transform_direction(xf, c["h"]).normal()
        cc["d"] = unreal.MathLibrary.inverse_transform_direction(xf, c["d"]).normal()
        conns.append(cc)
    return conns


def _spring_height(ptype):
    """Height where the passage's vertical walls end and the vault begins."""
    prof = PASSAGE_TYPES[ptype]["void_profile"]
    hw = max(abs(y) for (y, z) in prof)
    return max(z for (y, z) in prof if abs(y) >= hw - 0.5)


def _no_channel(profile, top):
    """Corner fill: the interior's full width from just above the walkway up to `top` (a wall
    height, never the vault: its end would show as slivers between the other vaults)."""
    ys = [y for (y, z) in profile]
    lo, hi = min(ys), max(ys)
    return [(lo + 1.0, BACK_FLOOR), (hi - 1.0, BACK_FLOOR), (hi - 1.0, top), (lo + 1.0, top)]


MITRE_FLOORS = True        # crossings: walkways/channel floors meet on clean diagonals (picture-frame mitres)


def _line_hit(p0, d0, p1, d1):
    """Intersection of two 2D lines p0 + t*d0 and p1 + s*d1 (None if parallel)."""
    den = d0[0] * d1[1] - d0[1] * d1[0]
    if abs(den) < 1e-6:
        return None
    t = ((p1[0] - p0[0]) * d1[1] - (p1[1] - p0[1]) * d1[0]) / den
    return (p0[0] + d0[0] * t, p0[1] + d0[1] * t)


def _crossing_mitres(conns):
    """For every pair of neighbouring arms (less than OPPOSITE_DEG apart): the picture-frame mitre
    line running from the corner where their walls meet (C) to the corner where their channel
    edges meet (D). Returns {(a, b): (C, D, ref_a)} with ref_a a point clearly on arm a's side."""
    angs = sorted(((math.degrees(math.atan2(c["h"].y, c["h"].x)) % 360.0, k) for k, c in enumerate(conns)))
    out = {}
    n = len(angs)
    for i in range(n if n > 2 else 1):
        (aa, a), (ab, bk) = angs[i], angs[(i + 1) % n]
        gap = (ab - aa) % 360.0
        if gap >= OPPOSITE_DEG or gap < 1.0:
            continue
        ca, cb = conns[a], conns[bk]
        ha, hb = (ca["h"].x, ca["h"].y), (cb["h"].x, cb["h"].y)
        ra, rb = (-ha[1], ha[0]), (-hb[1], hb[0])
        sa = 1.0 if (hb[0] * ra[0] + hb[1] * ra[1]) >= 0 else -1.0   # side of a facing b
        sb = 1.0 if (ha[0] * rb[0] + ha[1] * rb[1]) >= 0 else -1.0   # side of b facing a
        wa, wb = _void_half_width(ca["ptype"]), _void_half_width(cb["ptype"])
        qa = PASSAGE_TYPES[ca["ptype"]].get("water_half_width", wa / 2.0)
        qb = PASSAGE_TYPES[cb["ptype"]].get("water_half_width", wb / 2.0)
        C = _line_hit((ra[0] * sa * wa, ra[1] * sa * wa), ha, (rb[0] * sb * wb, rb[1] * sb * wb), hb)
        D = _line_hit((ra[0] * sa * qa, ra[1] * sa * qa), ha, (rb[0] * sb * qb, rb[1] * sb * qb), hb)
        if C is None or D is None:
            continue
        mid_a = sa * (wa + qa) / 2.0
        ref_a = (ha[0] * 2000.0 + ra[0] * mid_a, ha[1] * 2000.0 + ra[1] * mid_a)
        out[(a, bk)] = (C, D, ref_a)
    return out


def _outer_mitres(conns):
    """Outside corners of turns (see _outer_corners): the picture-frame line from the corner where
    the two walls meet (C) to the corner where the two channel edges meet (D), the two walkways
    meeting on it. Returns [(i, j, C, D, s_i, s_j)] (s = which side of each arm the corner is)."""
    out = []
    for i, j, C in _outer_corners(conns):
        ci, cj = conns[i], conns[j]
        hi, hj = (ci["h"].x, ci["h"].y), (cj["h"].x, cj["h"].y)
        ni, nj = (-hi[1], hi[0]), (-hj[1], hj[0])
        si = 1.0 if C[0] * ni[0] + C[1] * ni[1] > 0 else -1.0
        sj = 1.0 if C[0] * nj[0] + C[1] * nj[1] > 0 else -1.0
        qi = PASSAGE_TYPES[ci["ptype"]].get("water_half_width", _void_half_width(ci["ptype"]) / 2.0)
        qj = PASSAGE_TYPES[cj["ptype"]].get("water_half_width", _void_half_width(cj["ptype"]) / 2.0)
        D = _line_hit((ni[0] * si * qi, ni[1] * si * qi), hi, (nj[0] * sj * qj, nj[1] * sj * qj), hj)
        if D is None:
            continue
        out.append((i, j, C, D, si, sj))
    return out


MITRE_CLIP_TOP = 0.5   # walkway-level trim height (cm above the walkway) for room mitres
MITRE_CLIP_SHIFT = 0.73  # cm: trim plane offset from the exact wall corner (avoids degenerate booleans)


def _clip_walkways_at_mitres(voids, conns):
    """Rooms: where two passages leave close together their walkways overlap. Trim each
    passage's cutter at walkway level on the far side of the shared mitre line, so each
    walkway keeps its own floor up to that line (the seam runs down the middle, even when one
    of the passages slopes). Walls and vaults above walkway level are not touched."""
    mitres = _crossing_mitres(conns)
    for (a, b2), (C, D, ref_a) in mitres.items():
        dx, dy = D[0] - C[0], D[1] - C[1]
        ln = math.hypot(dx, dy)
        if ln < 1e-3:
            continue
        ux, uy = dx / ln, dy / ln
        nx, ny = -uy, ux                                  # normal of the mitre line
        if (ref_a[0] - C[0]) * nx + (ref_a[1] - C[1]) * ny < 0:
            nx, ny = -nx, -ny                             # now points to arm a's side
        for keep, side in ((b2, (nx, ny)), (a, (-nx, -ny))):
            # remove arm `keep`'s cutter below walkway level on the OTHER arm's side
            box = _new_mesh()
            fwd = V(side[0], side[1], 0.0)
            rot = unreal.MathLibrary.make_rot_from_x(fwd)   # yaw only: box Y runs along the mitre line
            # the line runs exactly through the corner where both inner walls meet; booleans
            # through that triple point drop faces, so the trim plane sits a hair off it
            cx, cy = C[0] + nx * MITRE_CLIP_SHIFT, C[1] + ny * MITRE_CLIP_SHIFT
            loc = V(cx + side[0] * 10000.0, cy + side[1] * 10000.0, -3000.0)
            gs("append_box")(box, PRIM, unreal.Transform(location=loc, rotation=rot),
                             20000.0, 40000.0, 3000.0 + MITRE_CLIP_TOP, 0, 0, 0, BASE)
            _finish_uvs(box)
            # the small riser this can leave (sloped neighbour) gets the walkway-edge texture
            table = _uv_table(conns[keep]["ptype"])
            lips = [e for e in (table or []) if abs(e[0][0] - e[1][0]) < 0.5 and max(e[0][1], e[1][1]) <= 0.5]
            if lips:
                _set_cell_all(box, _edge_cell(lips[0]))
            _boolean(voids[keep], box, SUBTRACT)


def _mitre_floors(mesh, conns, hub, room=False):
    """Crossing walkways meet like a picture frame: the walkway-level floor is split along each
    corner's mitre line (wall corner to channel corner) and every floor piece gets the walkway
    texturing of the arm it belongs to, so tiles run along their own arm right up to the seam.
    Only splits existing faces (no booleans), so the geometry itself is unchanged."""
    if len(conns) < 2:
        return mesh
    mitres = _crossing_mitres(conns)
    outer = [] if room else _outer_mitres(conns)
    # 1. split faces along every mitre line (inside corners, and the outside corners of turns)
    try:
        so = unreal.GeometryScriptMeshPlaneSliceOptions()
        so.set_editor_property("fill_holes", False)
        try:
            so.set_editor_property("gap_width", 0.0)
        except Exception:
            pass
        for (C, D) in [(m_[0], m_[1]) for m_ in mitres.values()] + [(o_[2], o_[3]) for o_ in outer]:
            dx, dy = D[0] - C[0], D[1] - C[1]
            ln = math.hypot(dx, dy)
            if ln < 1e-3:
                continue
            normal = V(-dy / ln, dx / ln, 0.0)
            frame = unreal.Transform(location=V(C[0], C[1], 0.0),
                                     rotation=unreal.MathLibrary.make_rot_from_z(normal))
            gs("apply_mesh_plane_slice")(mesh, frame, so)
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: mitre split skipped (%s); seams follow triangle edges" % e)

    # rooms: arms start at the wall (their floor inside the room is the base, not repainted)
    backs = [-(hub - 50.0) if room else _crossing_back(c, conns) for c in conns]
    if not room:
        # a straight-through arm's walkway carries on behind the centre (as its partner's), so it
        # still counts there when a side arm's corner mitre is decided
        for k, c in enumerate(conns):
            if any(j != k and _angle_between(c, o) >= OPPOSITE_DEG for j, o in enumerate(conns)):
                backs[k] = max(backs[k], _void_half_width(c["ptype"]))

    def outer_owner(px, py):
        """In the corner of a turn's outside (beyond both channels, on the corner's side): the
        arm on this point's side of the line from the wall corner to the channel corner."""
        for (i, j, C, D, si, sj) in outer:
            ok = True
            for k_, s_ in ((i, si), (j, sj)):
                c_ = conns[k_]
                hx, hy = c_["h"].x, c_["h"].y
                q_ = PASSAGE_TYPES[c_["ptype"]].get("water_half_width", 0.0)
                if (-px * hy + py * hx) * s_ < q_ - 2.0:
                    ok = False
                    break
            if not ok:
                continue
            dx, dy = D[0] - C[0], D[1] - C[1]
            side_p = dx * (py - C[1]) - dy * (px - C[0])
            ref = (D[0] + conns[i]["h"].x * 100.0, D[1] + conns[i]["h"].y * 100.0)   # on i's walkway
            side_r = dx * (ref[1] - C[1]) - dy * (ref[0] - C[0])
            return i if side_p * side_r > 0 else j
        return None

    def owner(px, py):
        k_ = outer_owner(px, py)
        if k_ is not None:
            return k_
        cands = []
        for k, c in enumerate(conns):
            hx, hy = c["h"].x, c["h"].y
            along = px * hx + py * hy
            side = -px * hy + py * hx
            if along >= -(backs[k] + 5.0) and abs(side) <= _void_half_width(c["ptype"]) * (1.0 + PROFILE_JITTER * k) + 2.0:
                cands.append(k)
        if not cands:
            if room:
                return None             # not on any arm: the room's own surfaces keep their UVs
            ang = math.degrees(math.atan2(py, px))
            return min(range(len(conns)), key=lambda k: abs((ang - math.degrees(math.atan2(conns[k]["h"].y, conns[k]["h"].x)) + 180.0) % 360.0 - 180.0))
        if len(cands) == 1:
            return cands[0]
        # prefer arms whose own walkway band (channel edge to wall) holds the point: an arm whose
        # walkway is narrower than the neighbour's would otherwise stretch its tiles past its edge
        # (rotated / smeared tiles on the wider walkway, e.g. where a 12 meets a 20)
        band = []
        for k in cands:
            c = conns[k]
            hx, hy = c["h"].x, c["h"].y
            side = abs(-px * hy + py * hx) / (1.0 + PROFILE_JITTER * k)
            q = PASSAGE_TYPES[c["ptype"]].get("water_half_width", 0.0)
            if q - 2.0 <= side <= _void_half_width(c["ptype"]) + 2.0:
                band.append(k)
        if len(band) == 1:
            return band[0]
        if band:
            cands = band
        losers = set()
        for (a, b2), (C, D, ref) in mitres.items():
            if a in cands and b2 in cands:
                # a mitre only splits the corner between its own two arms: the line, extended,
                # also crosses the walkway on the far side of the channel, which isn't theirs
                ha_, hb_ = (conns[a]["h"].x, conns[a]["h"].y), (conns[b2]["h"].x, conns[b2]["h"].y)
                den = ha_[0] * hb_[1] - ha_[1] * hb_[0]
                if abs(den) > 1e-6:
                    al = (px * hb_[1] - py * hb_[0]) / den        # p = al*ha + be*hb
                    be = (ha_[0] * py - ha_[1] * px) / den
                    if al < -10.0 or be < -10.0:
                        continue
                dx, dy = D[0] - C[0], D[1] - C[1]
                sp = dx * (py - C[1]) - dy * (px - C[0])
                sr = dx * (ref[1] - C[1]) - dy * (ref[0] - C[0])
                losers.add(b2 if sp * sr >= 0 else a)
        left = [k for k in cands if k not in losers] or cands
        ang = math.degrees(math.atan2(py, px))
        return min(left, key=lambda k: abs((ang - math.degrees(math.atan2(conns[k]["h"].y, conns[k]["h"].x)) + 180.0) % 360.0 - 180.0))

    # 2. repaint walkway-level, upward floor faces from their owning arm
    _ensure_uv_sets(mesh)
    for t in range(gs("get_num_triangle_i_ds")(mesh)):
        vs = _tri_positions(mesh, t)
        if not vs or max(abs(v.z) for v in vs) > 1.0:
            continue
        nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        if nrm.length() < 1e-6 or abs(nrm.normal().z) < 0.9:
            continue
        cx = sum(v.x for v in vs) / 3.0
        cy = sum(v.y for v in vs) / 3.0
        k = owner(cx, cy)
        if k is None:
            continue
        c = conns[k]
        table = _uv_table(c["ptype"])
        walks = [e for e in (table or []) if abs(e[0][1]) < 0.5 and abs(e[1][1]) < 0.5]
        if not walks:
            continue
        hx, hy = c["h"].x, c["h"].y
        mirror = bool(c.get("mirror"))
        seg = PASSAGE_TYPES[c["ptype"]]["segment_length"]
        s_start = hub + c["lead"]
        loc = []
        for v in vs:
            along = v.x * hx + v.y * hy
            y = (-v.x * hy + v.y * hx) / (1.0 + PROFILE_JITTER * k)
            y = -y if mirror else y
            x = (s_start - along) if mirror else (along - s_start)
            loc.append((x * 400.0 / seg, y))
        ty = sum(y for _, y in loc) / 3.0
        e = min(walks, key=lambda ed: (0 if (ed[0][0] + ed[1][0]) * ty >= 0 else 1,
                                       min(abs(ty - ed[0][0]), abs(ty - ed[1][0]))))
        span = (e[1][0] - e[0][0]) or 1.0
        _set_uv_triangle(mesh, 0, t, [_uv_on_edge(e, (y - e[0][0]) / span, x) for (x, y) in loc])
        cell = _edge_cell(e)
        if cell is not None:
            _set_uv_triangle(mesh, 1, t, [cell, cell, cell])
    return mesh


BEND_MIN_DEG = 45.0     # two-arm crossings bent at least this much get mitred corners
BEND_OVERLAP = 0.3      # cm: each arm's interior runs this far past the shared mitre plane


def _bend_mitre(conns):
    """Two-arm crossing (a corner): for each arm (back, plane point, plane normal) - how far its
    interior reaches back behind the centre, and the vertical mitre plane through the inner and
    outer wall corners beyond which it is cut off (normal points at the other arm). None when
    the crossing is not a plain corner."""
    if len(conns) != 2:
        return None
    ang = _angle_between(conns[0], conns[1])
    if ang < BEND_MIN_DEG or ang >= OPPOSITE_DEG:
        return None
    out = []
    for k in (0, 1):
        a, o = conns[k], conns[1 - k]
        ha, ho = (a["h"].x, a["h"].y), (o["h"].x, o["h"].y)
        ra, ro = (-ha[1], ha[0]), (-ho[1], ho[0])
        sa = 1.0 if (ho[0] * ra[0] + ho[1] * ra[1]) >= 0 else -1.0
        so = 1.0 if (ha[0] * ro[0] + ha[1] * ro[1]) >= 0 else -1.0
        wa, wo = _void_half_width(a["ptype"]), _void_half_width(o["ptype"])
        C = _line_hit((ra[0] * sa * wa, ra[1] * sa * wa), ha, (ro[0] * so * wo, ro[1] * so * wo), ho)
        O = _line_hit((-ra[0] * sa * wa, -ra[1] * sa * wa), ha, (-ro[0] * so * wo, -ro[1] * so * wo), ho)
        if C is None or O is None:
            return None
        dx, dy = O[0] - C[0], O[1] - C[1]
        ln = math.hypot(dx, dy)
        if ln < 1e-3:
            return None
        nx, ny = -dy / ln, dx / ln
        if (ho[0] * 2000.0 - C[0]) * nx + (ho[1] * 2000.0 - C[1]) * ny < 0:
            nx, ny = -nx, -ny                       # points at the other arm
        back = max(-(O[0] * ha[0] + O[1] * ha[1]), -(C[0] * ha[0] + C[1] * ha[1]), 0.0) + 30.0
        back = min(max(back, CROSSING_VOID_INSET), wa * 4.0)
        out.append((back, V(C[0] + nx * BEND_OVERLAP, C[1] + ny * BEND_OVERLAP, 0.0), V(nx, ny, 0.0)))
    return out


def _build_crossing_mesh(node, conns_world):
    conns = _local_conns(node, conns_world)
    hub = CROSSING_HUB
    voids, solids = [], []
    fill_top = min(_spring_height(c["ptype"]) for c in conns) - 1.0 if conns else 0.0
    bend = _bend_mitre(conns)
    levels = [hub] * len(conns) if bend else _crossing_levels(conns, hub)
    for k, c in enumerate(conns):
        jit = 1.0 + PROFILE_JITTER * k
        if bend:
            # corner (two arms, no straight-through): each arm's whole interior - walls, vault,
            # walkways and channel - runs on to the diagonal through the inner and outer wall
            # corners, like a mitred pipe bend, so walls, vaults and channels meet in the corner
            back, point, normal = bend[k]
            voids += _connection_voids(c, hub, back=back, scale=jit, clip=(point, normal))
        else:
            # full interior (with channel) from the centre outwards: channels meet in the middle
            voids += _connection_voids(c, hub, back=CROSSING_VOID_INSET, scale=jit, level_at=levels[k])
        # corner fill behind the centre: interior WITHOUT the channel, so it never cuts
        # channels across a neighbour's walkway
        # (corner fills behind the centre: see the outer-corner fills after this loop)
        # outer block: level through the hub, then following the slope (one swept shape)
        sb = _solid_half_width(c["ptype"])
        sback = max(sb, bend[k][0] + sb - _void_half_width(c["ptype"])) if bend else sb
        p = math.radians(c["pitch"])
        path = [V(-sback, 0, 0), V(hub + c["lead"], 0, 0)] if abs(c["pitch"]) < GEOM_LEVEL_EPS_DEG else \
            [V(-sback, 0, 0), V(max(hub, min(levels[k], hub + math.cos(p) * c["lead"] - 1.0)), 0, 0),
             V(hub + math.cos(p) * c["lead"], 0, math.sin(p) * c["lead"])]
        _outer_look(c["ptype"])                           # the tunnel piece's own outer shell
        sw = _sweep(_profile_raw(c, "outer_profile", jit), path)
        s_ = _new_mesh()
        gs("append_mesh")(s_, sw, unreal.Transform(rotation=unreal.MathLibrary.make_rot_from_x(c["h"])))
        _paint_outside(s_, c["ptype"])
        solids.append(s_)
    if not bend:
        voids += _outer_corner_voids(conns, hub)
    mesh = _new_mesh()
    gs("enable_material_i_ds")(mesh)
    _ensure_uv_sets(mesh)
    for piece in _disjoint(solids):
        for v in voids:
            _boolean(piece, v, SUBTRACT)
        gs("append_mesh")(mesh, piece, IDENT)
    if MITRE_FLOORS:
        try:
            mesh = _mitre_floors(mesh, conns, hub)
        except Exception as e:  # noqa
            unreal.log_warning("Sewer: %s floor mitres skipped (%s)" % (node.get_actor_label(), e))
    if FLATTEN_HUB_FLOOR:
        _flatten_hub_floor(mesh, min(levels) if levels else hub)
    if FOLD_AT_CORNERS and not bend:
        _fold_at_corners(mesh, conns, hub, levels)
    return mesh


FLATTEN_HUB_FLOOR = True   # crossings: snap the walkway-level floor flat inside the level zone
FLATTEN_TOL = 3.0          # cm: floor vertices this close to walkway height get snapped onto it


def _flatten_hub_floor(mesh, radius):
    """Inside a crossing every arm is level (slopes only start at `radius`), so the walkway floor
    should be one flat plane at Z 0 - like the box collision. The booleans between the arms' cutters
    left small steps (~1 cm) along the mitre seams; snap every vertex within FLATTEN_TOL of walkway
    height onto it."""
    r2 = (radius - 1.0) ** 2
    moved = 0
    for vid in range(gs("get_num_vertex_i_ds")(mesh)):
        r = gs("get_vertex_position")(mesh, vid)
        q = r[0] if isinstance(r, tuple) else r
        if not isinstance(q, unreal.Vector):
            continue
        if q.x * q.x + q.y * q.y < r2 and 0.0 < abs(q.z) < FLATTEN_TOL:
            gs("set_vertex_position")(mesh, vid, V(q.x, q.y, 0.0), True)
            moved += 1
    if moved:
        _normals(mesh)
    return moved


FOLD_AT_CORNERS = True    # crossings: a sloping arm's floor starts to slope on the line between the two
                           # corners where it meets its neighbours (not square across the arm)


def _arm_seam_points(conns, k):
    """All ends of the floor seams (mitre lines) arm k shares with its neighbours - the wall
    corner C and the channel corner D of each - as (s, t) in the arm's frame."""
    c = conns[k]
    hk = (c["h"].x, c["h"].y)
    nk = (-hk[1], hk[0])
    pts = []
    for (a, b), (C, D, _r) in _crossing_mitres(conns).items():
        if k in (a, b):
            pts += [C, D]
    for (i, j, C, D, _si, _sj) in _outer_mitres(conns):
        if k in (i, j):
            pts += [C, D]
    return [(P[0] * hk[0] + P[1] * hk[1], P[0] * nk[0] + P[1] * nk[1]) for P in pts]


def _arm_corner_line(conns, k):
    """The wall corners on the left (+) and right (-) side of arm k, as (s, t) in the arm's frame
    (s along it, t across it). Either may be None (no neighbour on that side)."""
    c = conns[k]
    hk = (c["h"].x, c["h"].y)
    nk = (-hk[1], hk[0])
    left = right = None
    pts = [C for (a, b), (C, D, _r) in _crossing_mitres(conns).items() if k in (a, b)]
    pts += [C for (i, j, C, D, _si, _sj) in _outer_mitres(conns) if k in (i, j)]
    for C in pts:
        sC, tC = C[0] * hk[0] + C[1] * hk[1], C[0] * nk[0] + C[1] * nk[1]
        if sC <= 0.0:
            continue
        if tC >= 0.0 and (left is None or sC > left[0]):
            left = (sC, tC)
        if tC < 0.0 and (right is None or sC > right[0]):
            right = (sC, tC)
    return left, right


def _fold_at_corners(mesh, conns, hub, levels):
    """A sloping arm is swept level up to a line square across it, then sloped. Where it meets its
    neighbours at different angles that fold doesn't follow the crossing's edge, leaving a wedge
    of sloped floor inside the crossing (or level floor sticking into the arm). Re-shape each
    sloping arm in Z so its fold runs exactly along the line between its two wall corners and
    the slope still reaches the passage at the same joint - floor, channel and walls together."""
    moved = 0
    for k, c in enumerate(conns):
        if abs(c["pitch"]) < GEOM_LEVEL_EPS_DEG:
            continue
        left, right = _arm_corner_line(conns, k)
        if left is None or right is None:
            continue      # a neighbour on one side only (straight through): the square fold is right
        # the fold runs at the angle of the corner-to-corner line, pushed out just far enough that
        # every seam this arm shares (wall corner to channel corner) lies on the flat floor - both
        # floors along a seam are then the same plane
        seam = _arm_seam_points(conns, k)
        slope_t = (right[0] - left[0]) / (right[1] - left[1]) if abs(right[1] - left[1]) > 1e-3 else 0.0
        offset = max([left[0] - slope_t * left[1]] + [sP - slope_t * tP for (sP, tP) in seam if sP > 0.0])
        left = (offset + slope_t * left[1], left[1])
        right = (offset + slope_t * right[1], right[1])
        p = math.radians(c["pitch"])
        cp, sp = math.cos(p), math.sin(p)
        J, Zj = hub + cp * c["lead"], sp * c["lead"]
        R = max(hub, min(levels[k], hub + cp * c["lead"] - 1.0))     # where the sweep folds now
        if J - R < 1.0:
            continue
        hk = (c["h"].x, c["h"].y)
        nk = (-hk[1], hk[0])
        band = _solid_half_width(c["ptype"]) + 5.0
        dt = right[1] - left[1]
        s_min = min(left[0], right[0], R) - 1.0

        def fold_at(t):
            s0 = left[0] + (t - left[1]) * (right[0] - left[0]) / dt if abs(dt) > 1e-3 else left[0]
            return max(1.0, min(s0, J - 20.0))

        for vid in range(gs("get_num_vertex_i_ds")(mesh)):
            r = gs("get_vertex_position")(mesh, vid)
            q = r[0] if isinstance(r, tuple) else r
            if not isinstance(q, unreal.Vector):
                continue
            sv, tv = q.x * hk[0] + q.y * hk[1], q.x * nk[0] + q.y * nk[1]
            if sv <= s_min or sv >= J or abs(tv) > band:
                continue
            old = 0.0 if sv <= R else Zj * (sv - R) / (J - R)
            s0 = fold_at(tv)
            new = 0.0 if sv <= s0 else Zj * (sv - s0) / (J - s0)
            if abs(new - old) > 1e-3:
                gs("set_vertex_position")(mesh, vid, V(q.x, q.y, q.z + new - old), True)
                moved += 1
    if moved:
        _normals(mesh)
    return moved


def rebake_crossings(labels=None):
    """Rebake only crossing node meshes (and their box collision) - the passages, water and the
    underside copies are left alone. labels: optional list of node labels (default: all crossings)."""
    use_definitive()
    _UV_TABLES.clear()
    _OUTER.clear()
    nodes = [a for a in _actors() if _is_node(a)]
    _, per_node = _gather(nodes, [])
    todo = [n for n in nodes if _is_crossing(_node_type(n)) and (labels is None or n.get_actor_label() in labels)]
    done, failed = [], []
    with unreal.ScopedSlowTask(len(todo), "Rebaking sewer crossings...") as task:
        task.make_dialog(True)
        for n in todo:
            if task.should_cancel():
                break
            task.enter_progress_frame(1, "Crossing " + n.get_actor_label())
            try:
                del _SLOTS[:]
                mesh = _build_node_mesh(n, per_node.get(n.get_path_name(), []))
                path = "%s/SM_SewerNode_%s" % (GENERATED_FOLDER, _safe(n.get_actor_label()))
                sm = _bake(mesh, path, list(_SLOTS), simple=False)
                comp = n.get_component_by_class(unreal.StaticMeshComponent)
                comp.modify()
                comp.set_static_mesh(sm)
                done.append(n.get_path_name())
            except Exception as e:  # keep going
                failed.append("%s: %s" % (n.get_actor_label(), e))
    if SIMPLE_COLLISION and done:
        import sewer_boxcol
        sewer_boxcol.apply_level_later(only=done)
    unreal.log("Sewer: rebaked %d crossings, %d failed" % (len(done), len(failed)))
    return len(done), failed


def _build_node_mesh(node, conns_world):
    ntype = _node_type(node)
    del _SLOTS[:]
    if _is_crossing(ntype):
        return _build_crossing_mesh(node, conns_world)
    cfg = NODE_TYPES[ntype]
    rin = cfg["inner_radius"]
    conns = _local_conns(node, conns_world)

    shell = unreal.EditorAssetLibrary.load_asset(cfg["shell_mesh"])
    if shell is None:
        raise RuntimeError("Shell mesh not found: " + cfg["shell_mesh"])
    raw = _new_mesh()
    gs("copy_mesh_from_static_mesh")(shell, raw, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                     unreal.GeometryScriptMeshReadLOD())
    # tiny odd yaw so the wall's vertical edges never sit exactly on a passage's centre line
    jitter = unreal.Transform(rotation=unreal.Rotator(roll=0, pitch=0, yaw=SHELL_JITTER_DEG))
    _remap_to_slots(raw, shell)                 # the wall keeps its own materials + UVs
    mesh = _new_mesh()
    gs("append_mesh")(mesh, raw, jitter)

    base = None
    base_sm = unreal.EditorAssetLibrary.load_asset(cfg["base_mesh"]) if cfg.get("base_mesh") else None
    if base_sm:
        base = _new_mesh()
        gs("copy_mesh_from_static_mesh")(base_sm, base, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                         unreal.GeometryScriptMeshReadLOD())
        _remap_to_slots(base, base_sm)
    elif cfg.get("base_mesh"):
        unreal.log_warning("Sewer: base mesh not found: " + cfg["base_mesh"])

    voids = []
    # passages leaving close together share floor far out of the room: keep each one level until
    # it is clear of its neighbours (two floors sloping different ways over the same ground left
    # steps and badly textured slivers), then slope to the same joint
    levels = _crossing_levels(conns, rin) if len(conns) > 1 else [rin] * len(conns)
    for k, c in enumerate(conns):
        c["level_at"] = levels[k]
        voids += _connection_voids(c, rin, level_at=levels[k])
    if MITRE_FLOORS and len(conns) > 1:
        _clip_walkways_at_mitres(voids, conns)

    # 1. the wall: only ever cut, never merged with anything (merges left slivers at the seam)
    for v in voids:
        _boolean(mesh, v, SUBTRACT)
    # the base owns the floor: remove the wall wherever the base is, so the two floor
    # surfaces never overlap at the doorways
    if base is not None and SUBTRACT_BASE:
        _boolean(mesh, base, SUBTRACT)

    # 2. collars: the passage's outer block from the wall's outer face to where the
    #    instanced passage starts. Trimmed by a plain cylinder just inside the wall's
    #    outer face (trimming by the wall mesh itself left slivers), made disjoint from
    #    each other (close-angle passages), cut by every void, then appended.
    clip = _new_mesh()
    gs("append_cylinder")(clip, PRIM, unreal.Transform(location=V(0, 0, -5000.0)),
                          cfg["outer_radius"] - COLLAR_OVERLAP, 10000.0, CIRCLE_STEPS, 0, True, BASE)
    collars = []
    for c in (conns if BUILD_COLLARS else []):
        s = _new_mesh()
        start = c["h"] * rin - c["d"] * SOLID_BACK
        _outer_look(c["ptype"])
        _append_prism(s, _profile(c, "outer_profile"), start, c["d"], SOLID_BACK + c["lead"])
        _paint_outside(s, c["ptype"])
        _boolean(s, clip, SUBTRACT)
        collars.append(s)
    # the collars overlap the wall's outer few cm; remove the wall there so the cut surfaces
    # exist only once (they z-fought before)
    for s in collars:
        _boolean(mesh, s, SUBTRACT)
    for piece in _disjoint(collars):
        for v in voids:
            _boolean(piece, v, SUBTRACT)
        gs("append_mesh")(mesh, piece, IDENT)

    if MITRE_FLOORS and len(conns) > 1:
        try:
            _mitre_floors(mesh, conns, rin, room=True)
        except Exception as e:  # noqa
            unreal.log_warning("Sewer: %s floor mitres skipped (%s)" % (node.get_actor_label(), e))

    # 3. the base exactly as modelled (UVs: shell/base keep theirs, cut faces carry the passages')
    if base is not None:
        # overhang the cut edge slightly (and sit 1 mm higher) so no hairline crack shows
        k = 1.0 + BASE_OVERHANG / max(1.0, rin)
        gs("append_mesh")(mesh, base, unreal.Transform(location=V(0, 0, 0.1), scale=V(k, k, 1.0)))
    return mesh


def _water_asset(ptype):
    """The passage type's modelled water strip (water_mesh) if it has one, otherwise a generated
    flat strip, segment_length long along +X, as wide as the channel, at WATER_Z."""
    pcfg = PASSAGE_TYPES[ptype]
    if pcfg.get("water_mesh"):
        sm = unreal.EditorAssetLibrary.load_asset(pcfg["water_mesh"])
        if sm:
            _set_nanite(sm)
            return sm
        unreal.log_warning("Sewer: water mesh not found, generating one: " + pcfg["water_mesh"])
    hw, L = pcfg["water_half_width"], pcfg["segment_length"]
    m = _new_mesh()
    _append_prism(m, [(-hw, WATER_Z - 0.2), (hw, WATER_Z - 0.2), (hw, WATER_Z), (-hw, WATER_Z)],
                  V(0, 0, 0), V(1, 0, 0), L)
    _finish_mesh(m, normals=True)
    return _bake(m, "%s/SM_SewerWater_%s" % (GENERATED_FOLDER, ptype), WATER_MATERIAL)


def _flow_data(edge, fade=0.0):
    """(dir_x, dir_y, speed, fade) for a passage: downhill, or A->B when level."""
    d = edge["dir"]
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, d.z))))
    sign = -1.0 if pitch > LEVEL_EPS_DEG else 1.0
    h = V(d.x, d.y, 0.0).normal() * sign
    return (h.x, h.y, WATER_BASE_SPEED + abs(pitch) * WATER_SPEED_PER_DEG, fade)


def _cap_asset(ptype):
    """End wall: the passage type's modelled end piece if it has one (inner face at the pivot,
    wall along +X), otherwise its solid profile extruded CAP_THICKNESS along +X."""
    path = PASSAGE_TYPES[ptype].get("end_mesh")
    if path:
        sm = unreal.EditorAssetLibrary.load_asset(path)
        if sm:
            return sm
        unreal.log_warning("Sewer: end piece not found (%s), using a generated cap" % path)
    m = _new_mesh()
    _append_prism(m, _oriented(PASSAGE_TYPES[ptype]["solid_profile"]), V(0, 0, 0), V(1, 0, 0), CAP_THICKNESS)
    _finish_mesh(m, normals=True)
    return _bake(m, "%s/SM_SewerCap_%s" % (GENERATED_FOLDER, ptype), NODE_MATERIAL)


# =============================================================================
# Network actor (HISMs)
# =============================================================================

def _add_hism(actor, name, static_mesh):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root = sds.k2_gather_subobject_data_for_instance(actor)[0]
    params = unreal.AddNewSubobjectParams(parent_handle=root,
                                          new_class=unreal.HierarchicalInstancedStaticMeshComponent,
                                          blueprint_context=None)
    handle, fail = sds.add_new_subobject(params)
    if str(fail):
        raise RuntimeError("Could not add HISM: %s" % fail)
    try:
        sds.rename_subobject(handle, unreal.Text(name))
    except Exception:
        pass
    data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
    comp = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    _set_nanite(static_mesh)
    comp.set_static_mesh(static_mesh)
    return comp


WATER_COLLISION_PROFILE = "NoCollision"   # water never blocks; swimming finds it by its component tag
WATER_COMPONENT_TAG = "Water_Sewage"       # read by TWBCharacterMovementComponent (swimming + underwater look)


def _water_collision(comp):
    try:
        comp.set_collision_profile_name(WATER_COLLISION_PROFILE)
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        tags = list(comp.component_tags)
        if unreal.Name(WATER_COMPONENT_TAG) not in tags:
            tags.append(unreal.Name(WATER_COMPONENT_TAG))
            comp.component_tags = tags
    except Exception as e:  # noqa
        unreal.log_warning("Sewer: water collision/tag not set (%s)" % e)


class _NetGrid(object):
    """One network actor per NETWORK_CELL square (created on demand), for World Partition."""

    def __init__(self):
        self.actors = {}

    @staticmethod
    def key(loc):
        c = NETWORK_CELL
        return int(math.floor(loc.x / c)), int(math.floor(loc.y / c))

    def at(self, loc):
        k = self.key(loc)
        a = self.actors.get(k)
        if a is None:
            eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            c = NETWORK_CELL
            a = eas.spawn_actor_from_class(unreal.StaticMeshActor, V((k[0] + 0.5) * c, (k[1] + 0.5) * c, 0.0),
                                           unreal.Rotator(0, 0, 0))
            a.set_actor_label("%s_%d_%d" % (NETWORK_LABEL, k[0], k[1]))
            try:
                a.set_folder_path(NETWORK_FOLDER)
            except Exception:
                pass
            self.actors[k] = a
        return a


def _net_actor(net, loc):
    return net.at(loc) if isinstance(net, _NetGrid) else net


class _Cells(object):
    """Instanced components of one mesh, one per CULL_CELL_SIZE cell (created on demand)."""

    def __init__(self, actor, name, mesh, custom_floats=0, material=None):
        self.actor, self.name, self.mesh, self.custom, self.comps = actor, name, mesh, custom_floats, {}
        self.material = material

    def get(self, loc):
        if isinstance(self.actor, _NetGrid):
            key = self.actor.key(loc)                  # one component per piece type per network actor
            name = self.name
        else:
            c = CULL_CELL_SIZE
            key = (int(math.floor(loc.x / c)), int(math.floor(loc.y / c)), int(math.floor(loc.z / c)))
            name = "%s_%d_%d_%d" % ((self.name,) + key)
        comp = self.comps.get(key)
        if comp is None:
            comp = _add_hism(_net_actor(self.actor, loc), name, self.mesh)
            if self.custom:
                try:
                    comp.set_editor_property("num_custom_data_floats", self.custom)
                except Exception as ex:  # noqa
                    unreal.log_warning("Sewer: no per-instance custom data (%s)" % ex)
            if self.material:
                comp.set_material(0, self.material)
            if "WaterUnder" in self.name:
                comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)   # the ripple layer has it
            elif "Water" in self.name:
                _water_collision(comp)
            self.comps[key] = comp
        return comp


def _mid(xf, length):
    """World centre of an instance that runs `length` (unscaled) along its local +X."""
    return unreal.MathLibrary.transform_location(xf, V(length * 0.5, 0, 0))


def _add_instance(comp, xf):
    try:
        return comp.add_instance(xf, True)  # world space
    except TypeError:
        return comp.add_instance(xf)


def _longer(xf, extra, mesh_length):
    """Same transform, stretched `extra` cm further along its +X (for water overlaps)."""
    s3 = xf.scale3d
    return unreal.Transform(location=xf.translation, rotation=xf.rotation.rotator(),
                            scale=V(s3.x + extra / mesh_length, s3.y, s3.z))


def _raised(xf):
    """The ripple layer, lifted just above the plain water layer (v5); unchanged otherwise."""
    if not WATER_UNDER_MATERIAL:
        return xf
    return unreal.Transform(location=xf.translation + V(0, 0, WATER_LAYER_GAP), rotation=xf.rotation.rotator(),
                            scale=xf.scale3d)


def _add_water(comp, xf, flow):
    idx = _add_instance(comp, xf)
    if isinstance(idx, int) and idx >= 0:
        for k, v in enumerate(flow):
            try:
                comp.set_custom_data_value(idx, k, float(v), True)
            except Exception:
                return idx
    return idx


def _segment_transforms(edge):
    seg = PASSAGE_TYPES[edge["ptype"]]["segment_length"]
    length, d, start = edge["length"], edge["dir"], edge["start"]
    if length < MIN_RUN:
        return []
    count = max(1, int(round(length / seg)))
    step = length / count
    sx = step / seg
    out = []
    for i in range(count):
        if PASSAGE_MESH_POINTS_PLUS_X:
            loc, rot = start + d * (i * step), unreal.MathLibrary.make_rot_from_x(d)
        else:
            loc, rot = start + d * ((i + 1) * step), unreal.MathLibrary.make_rot_from_x(d * -1.0)
        out.append(unreal.Transform(location=loc, rotation=rot, scale=V(sx, 1.0, 1.0)))
    return out


def _strip_transform(start, d, length, mesh_length):
    """One stretched instance covering `length` from `start` along `d`."""
    sx = length / mesh_length
    if PASSAGE_MESH_POINTS_PLUS_X:
        return unreal.Transform(location=start, rotation=unreal.MathLibrary.make_rot_from_x(d), scale=V(sx, 1.0, 1.0))
    return unreal.Transform(location=start + d * length, rotation=unreal.MathLibrary.make_rot_from_x(d * -1.0),
                            scale=V(sx, 1.0, 1.0))


def _lead_water_transforms(edge):
    """Water through the node walls up to where the passage run starts, as (transform, fade).
    Rooms: tucked under the base edge. Crossings: starts exactly at the hub patch and eases
    in from still water (fade 1 = still at the strip start, 2 = still at its end)."""
    seg = PASSAGE_TYPES[edge["ptype"]]["segment_length"]
    d, out = edge["dir"], []
    if edge["lead_a"] > 0:
        if edge["cross_a"]:
            pass                     # part of the crossing's own water surface
        else:
            out.append((_strip_transform(edge["bend_a"] - d * WATER_TUCK, d, edge["lead_a"] + WATER_TUCK, seg), 0.0))
    if edge["lead_b"] > 0:
        if edge["cross_b"]:
            pass
        else:
            out.append((_strip_transform(edge["end"], d, edge["lead_b"] + WATER_TUCK, seg), 0.0))
    if edge["length"] < MIN_RUN:  # no segments placed: bridge the gap too
        out.append((_strip_transform(edge["start"], d, max(edge["length"], 0.0), seg), 0.0))
    return out


def _water_joint(node_loc, c, rin):
    """Where a crossing's water meets the passage water on connection c: the passage run's end
    point, the passage's own direction (A->B) and the two exact corners of its water strip
    there, plus the left/right labels seen from the crossing."""
    hw = PASSAGE_TYPES[c["ptype"]]["water_half_width"]
    h = V(c["h"].x, c["h"].y, 0.0).normal()
    P = node_loc + h * rin + c["d"] * c["lead"]
    e = c["d"] * -1.0 if c.get("mirror") else c["d"]
    rot = unreal.MathLibrary.make_rot_from_x(e)
    right, up = rot.get_right_vector(), rot.get_up_vector()
    P = P + c["d"] * WATER_OVERLAP       # reach just under the passage water (see WATER_OVERLAP)
    a, b = P + right * hw + up * WATER_Z, P - right * hw + up * WATER_Z
    nl = V(-h.y, h.x, 0.0)
    if (a - node_loc).dot(nl) < (b - node_loc).dot(nl):
        a, b = b, a
    return h, nl, hw, a, b          # a = left corner, b = right corner (looking out from the node)


def _hub_water_asset(node, conns_world):
    """Water for a whole crossing as ONE surface: the union of every connection's channel strip
    from the crossing centre out to where its passage water starts. Level inside the hub,
    following each passage's slope beyond it, and ending exactly on the passage water strip's
    first/last edge (same vertices), so nothing overlaps and nothing gaps."""
    loc = node.get_actor_location()
    rin = _radii(_node_type(node))[0]
    zf = WATER_Z                       # local: level water height
    arms = []
    field = _FLOW_FIELD
    npath = node.get_path_name()
    Sn, Tn = field["nodes"].get(npath, (0.0, 0.0))
    for c in conns_world:
        h, nl, hw, L, R = _water_joint(loc, c, rin)
        # where the passage water starts: its distance / travel-time values there (relative to
        # this crossing's own) and its cross-channel axis, so the ripples carry on unbroken
        Pw = loc + h * rin + c["d"] * c["lead"] + c["d"] * WATER_OVERLAP
        ed = field["edges"].get(c.get("eid"))
        if ed is not None:
            Sj, Tj = _flow_field_at(ed, (Pw - ed["bend_a"]).dot(ed["dir"]))
            if npath == ed["b"] and "SBn" in ed:      # same water, counted from this end
                Sj += ed["SBn"] - ed["SB"]
                Tj += ed["TBn"] - ed["TB"]
            right = unreal.MathLibrary.make_rot_from_x(ed["dir"]).get_right_vector()
            if HUB_FLOW_VERSION in (2, 4, 5):
                right = right * ed["vsign"]
        else:
            Sj, Tj, right = Sn, Tn, V(-h.y, h.x, 0.0)
        right = V(right.x, right.y, 0.0)
        aj = (Pw - loc).x * h.x + (Pw - loc).y * h.y
        arms.append({"h": h, "nl": nl, "hw": hw, "L": L - loc, "R": R - loc,
                     "ang": math.atan2(h.y, h.x), "dS": Sj - Sn, "dT": Tj - Tn, "aj": max(1.0, aj),
                     "Pl": Pw - loc, "right": right})

    def arm_val(a, p, at_joint=False):
        """(distance, time, cross axis) at local point p on arm a."""
        psi = (p.x - a["Pl"].x) * a["right"].x + (p.y - a["Pl"].y) * a["right"].y
        if at_joint:
            return (a["dS"], a["dT"], psi, 1.0)
        k = max(0.0, min(1.0, (p.x * a["h"].x + p.y * a["h"].y) / a["aj"]))
        return (a["dS"] * k, a["dT"] * k, psi, 1.0)
    arms.sort(key=lambda a: a["ang"])
    n = len(arms)

    def along(a, p):
        return p.x * a["h"].x + p.y * a["h"].y

    def zat(a, p):
        """Water height at p inside arm a: level up to rin, then sloping to the joint."""
        s_end = (along(a, a["L"]) + along(a, a["R"])) * 0.5
        z_end = (a["L"].z + a["R"].z) * 0.5
        s = along(a, p)
        if s <= rin or s_end <= rin + 1e-3:
            return zf
        return zf + (z_end - zf) * min(1.0, (s - rin) / (s_end - rin))

    # corner between arm i's left edge and arm i+1's right edge (or an arc round the centre)
    joins = []
    for i in range(n):
        a, b = arms[i], arms[(i + 1) % n]
        gap = (b["ang"] - a["ang"]) % (2 * math.pi) if n > 1 else 2 * math.pi
        c = None
        if n > 1 and (gap < math.pi - 1e-3 or gap > math.pi + 0.05):
            # the two channel edges meet in a sharp corner, inside or outside (like the walls)
            p0 = a["nl"] * a["hw"]
            q0 = b["nl"] * -b["hw"]
            den = a["h"].x * b["h"].y - a["h"].y * b["h"].x
            t = ((q0.x - p0.x) * b["h"].y - (q0.y - p0.y) * b["h"].x) / den
            c = p0 + a["h"] * t
            if gap > math.pi and math.hypot(c.x, c.y) > 6.0 * max(a["hw"], b["hw"]):
                c = None                         # extremely sharp bend: round it off instead
        if c is not None:
            joins.append([V(c.x, c.y, zat(a, c) if along(a, c) > along(b, c) else zat(b, c))])
        else:
            a0 = math.atan2(a["nl"].y, a["nl"].x)
            a1 = a0 + gap - math.pi             # from arm i's left normal round to arm i+1's right normal
            steps = max(1, int(math.ceil((a1 - a0) / math.radians(30))))
            pts = []
            for k in range(steps + 1):
                f = float(k) / steps
                ang, r = a0 + (a1 - a0) * f, a["hw"] + (b["hw"] - a["hw"]) * f
                pts.append(V(math.cos(ang) * r, math.sin(ang) * r, zf))
            joins.append(pts)

    verts, tris, flows, varm, owners = [], [], [], [], []

    def vid(p, f=(0.0, 0.0, 0.0, 0.0), arm=None):
        verts.append(p)
        flows.append(f)
        varm.append(arm)
        return len(verts) - 1

    def avg(fs):
        return (sum(f[0] for f in fs) / max(1, len(fs)), sum(f[1] for f in fs) / max(1, len(fs)))

    centre = vid(V(0, 0, zf))
    inner = []                                  # inner (level) outline, counter-clockwise
    quads = []
    for i in range(n):
        a = arms[i]
        prev = joins[i - 1][-1]                 # where arm i's right edge starts
        nxt = joins[i][0]                       # where arm i's left edge ends
        R260 = a["nl"] * -a["hw"] + a["h"] * rin
        L260 = a["nl"] * a["hw"] + a["h"] * rin
        rk = vid(V(R260.x, R260.y, zf), arm_val(a, R260), i) if along(a, prev) < rin - 1e-3 else None
        lk = vid(V(L260.x, L260.y, zf), arm_val(a, L260), i) if along(a, nxt) < rin - 1e-3 else None
        inner.append(("arm", i, rk, lk))
        quads.append((i, rk, lk))
    # build the outline ids: joins between arms
    join_ids = [[vid(p) for p in pts] for i, pts in enumerate(joins)]
    outline = []
    for i in range(n):
        _, _, rk, lk = inner[i]
        if rk is not None:
            outline.append(rk)
        if lk is not None:
            outline.append(lk)
        outline.extend(join_ids[i])
    # remove consecutive duplicates (also wrap-around)
    clean = []
    for v in outline:
        if not clean or clean[-1] != v:
            clean.append(v)
    if len(clean) > 1 and clean[0] == clean[-1]:
        clean.pop()

    def tri(i0, i1, i2, owner=None):
        p0, p1, p2 = verts[i0], verts[i1], verts[i2]
        cz = (p1.x - p0.x) * (p2.y - p0.y) - (p1.y - p0.y) * (p2.x - p0.x)
        if abs(cz) < 1e-6:
            return
        if owner is None:      # the arm this triangle belongs to: one of its own corners, else the nearest
            owner = next((varm[k] for k in (i0, i1, i2) if varm[k] is not None), None)
        if owner is None:
            cx, cy = (p0.x + p1.x + p2.x) / 3.0, (p0.y + p1.y + p2.y) / 3.0
            owner = max(range(n), key=lambda j: cx * arms[j]["h"].x + cy * arms[j]["h"].y) if n else 0
        # Unreal is left-handed: clockwise seen from above = facing up
        tris.append((i0, i2, i1) if cz > 0 else (i0, i1, i2))
        owners.append(owner)

    for k in range(len(clean)):
        tri(centre, clean[k], clean[(k + 1) % len(clean)])
    # sloping part of each arm: from its level edge (or the inner corners) to the passage joint
    for i, rk, lk in quads:
        a = arms[i]
        r0 = rk if rk is not None else join_ids[i - 1][-1]
        l0 = lk if lk is not None else join_ids[i][0]
        Rv, Lv = vid(a["R"], arm_val(a, a["R"], True), i), vid(a["L"], arm_val(a, a["L"], True), i)
        tri(r0, Rv, Lv, i)
        tri(r0, Lv, l0, i)

    if HUB_FLOW_VERSION in (2, 4, 5):
        return _hub_water_v2(node, verts, tris, arms)

    m = _new_mesh()
    ids = []
    for p in verts:
        r = gs("add_vertex_to_mesh")(m, p, False)
        ids.append(r[1] if isinstance(r, tuple) else r)
    tids = []
    for t in tris:
        r = gs("add_triangle_to_mesh")(m, unreal.IntVector(ids[t[0]], ids[t[1]], ids[t[2]]), 0, False)
        tids.append(r[1] if isinstance(r, tuple) else r)
    _finish_mesh(m, normals=True)
    # UV 2 = (distance, travel time) relative to the crossing's own (per-instance data), UV 3 =
    # cross-channel axis: they meet each passage's values exactly where its water starts
    # Every triangle uses ONE arm's values at all three corners (UVs are per triangle corner), so
    # no triangle mixes two arms' directions; the shared lines between arms (centre -> corners)
    # have weight 0 on both sides = the calm drifting water, so they match too.
    _ensure_uv_sets(m, 4)

    def corner(k, j):
        if varm[k] == j:
            return flows[k]
        f = arm_val(arms[j], verts[k])
        return (f[0], f[1], f[2], 0.0)
    for t, tid, j in zip(tris, tids, owners):
        cs = [corner(k, j) for k in t]
        _set_uv_triangle(m, 2, tid, [(c[0], c[1]) for c in cs])
        _set_uv_triangle(m, 3, tid, [(c[2], c[3]) for c in cs])
    sm = _bake(m, "%s/SM_SewerHubWater%s_%s" % (GENERATED_FOLDER, HUB_ASSET_SUFFIX, _safe(node.get_actor_label())),
               WATER_MATERIAL)
    try:   # keep UV 2/3 exact (they carry data, not texture coords) and don't let a lightmap overwrite them
        ses = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        bs = ses.get_lod_build_settings(sm, 0)
        bs.set_editor_property("use_full_precision_u_vs", True)
        bs.set_editor_property("generate_lightmap_u_vs", False)
        ses.set_lod_build_settings(sm, 0, bs)
        unreal.EditorAssetLibrary.save_loaded_asset(sm, False)
    except Exception as ex:  # noqa
        unreal.log_warning("Sewer: hub water build settings not set (%s)" % ex)
    return sm


WATER_UNDER_MATERIAL = None   # v5: a second water layer under the ripples (Single Layer Water colour)
WATER_LAYER_GAP = 0.75        # v5: cm the ripple layer sits above it
HUB_ASSET_SUFFIX = ""      # crossing water asset name tag (another test variant keeps its own copies)
HUB_FLOW_VERSION = 1      # 1 = streams fade into calm drifting water in the middle, 2 = smooth through-flow
                          # (turns exact), 4 = v2 + every turning corner of 3+ way crossings exact
HUB_V2_SUBDIV = 5         # v2: each crossing triangle is split into this^2 for the smooth solve
HUB_V2_TILE = 200.0       # v2: must match the material's TileSize (arms are shifted by whole tiles)
FLOW_LOOP_WRAP = True     # loops of passages: every passage keeps its exact length / travel time and
                          # the loop is closed by whole ripple repeats at one end of one passage
                          # (invisible) - instead of stretching a few long passages' ripples to fit
FLOW_WRAP_BALANCE = 0.3   # the material's StretchBalance / FlowRefSpeed / TileSize (read from
FLOW_WRAP_VREF = 60.0     # WATER_MATERIAL when building, these are only the fallback): a whole ripple
FLOW_WRAP_TILE = 200.0    # repeat depends on them. Changed in the material -> rebuild.


def _read_flow_material():
    """The water material's StretchBalance, FlowRefSpeed and TileSize (what one ripple repeat is)."""
    global FLOW_WRAP_BALANCE, FLOW_WRAP_VREF, FLOW_WRAP_TILE
    try:
        mi = unreal.EditorAssetLibrary.load_asset(WATER_MATERIAL) if WATER_MATERIAL else None
        if mi is None:
            return
        mel = unreal.MaterialEditingLibrary
        for name, var in (("StretchBalance", "FLOW_WRAP_BALANCE"), ("FlowRefSpeed", "FLOW_WRAP_VREF"),
                          ("TileSize", "FLOW_WRAP_TILE")):
            try:
                v = mel.get_material_instance_scalar_parameter_value(mi, name)
                if v is not None and float(v) > 0.0:
                    globals()[var] = float(v)
            except Exception:
                pass
        global HUB_V2_TILE
        HUB_V2_TILE = FLOW_WRAP_TILE          # the crossing water's cross axis shifts by whole tiles too
        unreal.log("Sewer: water material: StretchBalance %.2f, FlowRefSpeed %.1f, TileSize %.0f"
                   % (FLOW_WRAP_BALANCE, FLOW_WRAP_VREF, FLOW_WRAP_TILE))
    except Exception as ex:  # noqa
        unreal.log_warning("Sewer: water material settings not read (%s)" % ex)


_HUB_V2_ITERS = []
HUB_V2_GRID = 20.0        # v2: cm between the regular grid points the smooth fill is solved on


HUB_V2_CALM = False       # v2: fade badly distorted spots to calm water (off: always the flow)
HUB_V2_MAX_ANISO = 2.5    # v2: ripples squashed more than this one way vs the other -> calm water there
HUB_V2_SCALE = (0.35, 3.0)  # v2: ripples bigger/smaller than this vs normal -> calm water there


def _hub_v2_quality(pts, ftris, vals, fixed, lam=0.3, vref=60.0, tile=200.0):
    """How undistorted the flowing ripples are at each vertex (1 = fine, 0 = badly stretched,
    pinched or squashed). Where they'd break (the middle of uneven crossings, dead corners of
    sharp bends, thin wedges) the material shows the calm wandering water instead."""
    k = (1.0 - lam) * vref / tile
    tq = []
    for t in ftris:
        p0, p1, p2 = pts[t[0]], pts[t[1]], pts[t[2]]
        e1x, e1y, e2x, e2y = p1.x - p0.x, p1.y - p0.y, p2.x - p0.x, p2.y - p0.y
        det = e1x * e2y - e1y * e2x
        if abs(det) < 1e-6:
            tq.append(None)
            continue
        grads = []
        for f in (lambda v: lam * v[0] / tile + k * v[1], lambda v: v[2] / tile):
            f0, f1, f2 = f(vals[t[0]]), f(vals[t[1]]), f(vals[t[2]])
            d1, d2 = f1 - f0, f2 - f0
            grads.append(((d1 * e2y - d2 * e1y) / det, (d2 * e1x - d1 * e2x) / det))
        (a, b), (c, d) = grads
        # singular values of the 2x2 mapping
        s1 = a * a + b * b + c * c + d * d
        dd = abs(a * d - b * c)
        r = math.sqrt(max(0.0, s1 * s1 - 4.0 * dd * dd))
        sig1, sig2 = math.sqrt((s1 + r) * 0.5), math.sqrt(max(0.0, (s1 - r) * 0.5))
        aniso = sig1 / max(1e-9, sig2)
        scale = math.sqrt(sig1 * sig2) * tile
        qa = max(0.0, min(1.0, (HUB_V2_MAX_ANISO * 1.4 - aniso) / (HUB_V2_MAX_ANISO * 0.4)))
        lo, hi = HUB_V2_SCALE
        qs = max(0.0, min(1.0, (scale - lo * 0.7) / (lo * 0.3), (hi * 1.4 - scale) / (hi * 0.4)))
        tq.append(min(qa, qs))
    vq = [[] for _ in pts]
    for t, q in zip(ftris, tq):
        if q is not None:
            for x in t:
                vq[x].append(q)
    q = [min(v) if v else 0.0 for v in vq]
    # soften the edges of the calm patches a little, keep each passage mouth fully flowing
    nb = [set() for _ in pts]
    for t in ftris:
        for x in range(3):
            nb[t[x]].add(t[(x + 1) % 3])
            nb[t[(x + 1) % 3]].add(t[x])
    for _ in range(3):
        q = [qq if not nb[i] else 0.5 * qq + 0.5 * min(qq, sum(q[j] for j in nb[i]) / len(nb[i]))
             for i, qq in enumerate(q)]
    for k_ in fixed:
        q[k_] = 1.0
    return q


def _hub_v2_bend(pts, arms, fixed, vals, psi, off):
    """Two-passage crossings (turns): the water goes round the inside corner like a curved
    channel. Straight from each mouth up to the corner's line, then round an arc about the inner
    corner, the cross axis being the distance from that corner (so the outside of the turn is
    the outside of the channel), the along-flow values spread evenly by the centre-line length."""
    if len(arms) != 2:
        return False
    A, B = arms
    gap = (B["ang"] - A["ang"]) % (2 * math.pi)
    if abs(gap - math.pi) < math.radians(3):
        return False                       # straight through: the plain fill is already exact
    if gap > math.pi:
        A, B = B, A                        # A's left wall and B's right wall make the inside corner
    p0 = A["nl"] * A["hw"]
    q0 = B["nl"] * -B["hw"]
    den = A["h"].x * B["h"].y - A["h"].y * B["h"].x
    if abs(den) < 1e-6:
        return False
    t = ((q0.x - p0.x) * B["h"].y - (q0.y - p0.y) * B["h"].x) / den
    c = p0 + A["h"] * t                    # inside corner
    # turn about a point BEHIND the inside corner (one half-width into the wall), so the water
    # hugging the inside corner isn't squeezed into a point there
    bx, by = A["h"].x + B["h"].x, A["h"].y + B["h"].y
    bl = math.hypot(bx, by)
    E = 0.5 * (A["hw"] + B["hw"])
    if bl > 1e-6:
        bx, by = bx / bl, by / bl
        sn = abs(bx * A["h"].y - by * A["h"].x)
        c = V(c.x + bx * E / max(0.2, sn), c.y + by * E / max(0.2, sn), 0.0)
    ia, ib = arms.index(A), arms.index(B)

    def unit_into(a):                      # across the arm, from the inside wall into the channel
        n_ = V(a["nl"].x, a["nl"].y, 0.0)
        if (a["Pl"].x - c.x) * n_.x + (a["Pl"].y - c.y) * n_.y < 0:
            n_ = n_ * -1.0
        return n_
    na, nb_ = unit_into(A), unit_into(B)
    sa = na.x * A["right"].x + na.y * A["right"].y
    sb = nb_.x * B["right"].x + nb_.y * B["right"].y
    if sa * sb < 0:
        return False                       # (only in a closed loop of turns: see _flow_vsigns)
    sgn = 1.0 if sa > 0 else -1.0
    # how far the turning point sits from each inside wall (= E unless clamped above)
    ea = abs((c.x - A["Pl"].x) * na.x + (c.y - A["Pl"].y) * na.y) - A["hw"]
    eb = abs((c.x - B["Pl"].x) * nb_.x + (c.y - B["Pl"].y) * nb_.y) - B["hw"]
    La = max(1.0, (A["Pl"].x - c.x) * A["h"].x + (A["Pl"].y - c.y) * A["h"].y)
    Lb = max(1.0, (B["Pl"].x - c.x) * B["h"].x + (B["Pl"].y - c.y) * B["h"].y)
    sweep = math.acos(max(-1.0, min(1.0, na.x * nb_.x + na.y * nb_.y)))
    arc = (0.5 * (A["hw"] + B["hw"]) + 0.5 * (ea + eb)) * sweep
    D = La + arc + Lb
    offa, offb = off[ia], off[ib]
    if abs(offa - offb) > 1e-3:
        return False

    meet = A["dT"] * B["dT"] > 0               # water runs in along both (or out along both)
    fm = (La + 0.5 * arc) / D

    def along_vals(f):                     # f = distance from A's mouth / D
        if meet:                           # the two flows meet halfway round the turn
            if f <= fm:
                g = 1.0 - f / fm
                return (A["dS"] * g, A["dT"] * g)
            g = (f - fm) / max(1e-6, 1.0 - fm)
            return (B["dS"] * g, B["dT"] * g)
        return (A["dS"] + (B["dS"] - A["dS"]) * f, A["dT"] + (B["dT"] - A["dT"]) * f)
    Sa_line = along_vals(La / D)
    Sb_line = along_vals((La + arc) / D)
    for k, p in enumerate(pts):
        if k in fixed:
            continue
        wx, wy = p.x - c.x, p.y - c.y
        da = wx * A["h"].x + wy * A["h"].y
        db = wx * B["h"].x + wy * B["h"].y
        if da >= 0.0 and da >= db:
            f = max(0.0, min(1.0, 1.0 - da / La))          # 1 at the corner line, 0 at the mouth
            S_, T_ = along_vals((La - min(da, La)) / D)
            vals[k] = [S_, T_, psi(A, p) + offa]
        elif db >= 0.0:
            S_, T_ = along_vals((La + arc + min(db, Lb)) / D)
            vals[k] = [S_, T_, psi(B, p) + offb]
        else:
            r = math.hypot(wx, wy)
            if r < 1e-3:
                fr = 0.5
            else:
                ux, uy = wx / r, wy / r
                a1 = math.acos(max(-1.0, min(1.0, ux * na.x + uy * na.y)))
                a2 = math.acos(max(-1.0, min(1.0, ux * nb_.x + uy * nb_.y)))
                fr = a1 / max(1e-6, a1 + a2)
            S_, T_ = along_vals((La + arc * fr) / D)
            hw = A["hw"] + (B["hw"] - A["hw"]) * fr + ea + (eb - ea) * fr
            vals[k] = [S_, T_, sgn * (r - hw) + offa]
    _HUB_V2_ITERS.append("bend")
    return True


def _hub_v2_corner_pin(arms, psi, off, turns=True):
    """Three or more passages: the same 'turn round the inside corner' as a two-way turn, at
    every corner where the water actually turns (in along one passage, out along the next),
    plus each passage's own straight run up to its corners. Returns a function giving the
    exact values at a point covered by one of those, or None (the middle, the corners where
    flows meet head-on or split apart) - those spots are filled smoothly in between."""
    n = len(arms)
    corners = []
    for i in range(n):
        A, B = arms[i], arms[(i + 1) % n]
        gap = (B["ang"] - A["ang"]) % (2 * math.pi)
        if gap >= math.pi - math.radians(3):
            continue
        p0 = A["nl"] * A["hw"]
        q0 = B["nl"] * -B["hw"]
        den = A["h"].x * B["h"].y - A["h"].y * B["h"].x
        if abs(den) < 1e-6:
            continue
        t = ((q0.x - p0.x) * B["h"].y - (q0.y - p0.y) * B["h"].x) / den
        c = p0 + A["h"] * t
        bx, by = A["h"].x + B["h"].x, A["h"].y + B["h"].y
        bl = math.hypot(bx, by)
        E = 0.5 * (A["hw"] + B["hw"])
        if bl > 1e-6:
            bx, by = bx / bl, by / bl
            sn = abs(bx * A["h"].y - by * A["h"].x)
            c = V(c.x + bx * E / max(0.2, sn), c.y + by * E / max(0.2, sn), 0.0)

        def unit_into(a, c=c):
            n_ = V(a["nl"].x, a["nl"].y, 0.0)
            if (a["Pl"].x - c.x) * n_.x + (a["Pl"].y - c.y) * n_.y < 0:
                n_ = n_ * -1.0
            return n_
        na, nb_ = unit_into(A), unit_into(B)
        sa = na.x * A["right"].x + na.y * A["right"].y
        sb = nb_.x * B["right"].x + nb_.y * B["right"].y
        ea = abs((c.x - A["Pl"].x) * na.x + (c.y - A["Pl"].y) * na.y) - A["hw"]
        eb = abs((c.x - B["Pl"].x) * nb_.x + (c.y - B["Pl"].y) * nb_.y) - B["hw"]
        ok = sa * sb > 0 and abs(off[i] - off[(i + 1) % n]) < 1e-3
        corners.append({"i": i, "j": (i + 1) % n, "c": c, "na": na, "nb": nb_, "ok": ok,
                        "sgn": 1.0 if sa > 0 else -1.0, "ea": ea, "eb": eb,
                        "rmax": max(ea, eb) + 2.0 * max(A["hw"], B["hw"])})
    # where each passage's straight run starts: the corner lines on either side of it
    start = [-1e9] * n
    for cn in corners:
        for k in (cn["i"], cn["j"]):
            a = arms[k]
            start[k] = max(start[k], cn["c"].x * a["h"].x + cn["c"].y * a["h"].y)
    for k, a in enumerate(arms):
        if start[k] < -1e8:
            start[k] = a["aj"] * 0.5            # no corner beside it: only its outer half is fixed

    def arm_vals(k, p):
        a = arms[k]
        al = (p.x * a["h"].x + p.y * a["h"].y) / a["aj"]
        return (a["dS"] * al, a["dT"] * al, psi(a, p) + off[k])

    def pin(p):
        # exact only where ONE thing claims the point: where two turns (or a turn and a straight
        # run) overlap - the middle of busy crossings - they disagree, so that's filled smoothly
        found = []
        for k, a in enumerate(arms):
            al = p.x * a["h"].x + p.y * a["h"].y
            if al >= start[k] - 1e-3:
                cross = abs((p.x - a["Pl"].x) * a["nl"].x + (p.y - a["Pl"].y) * a["nl"].y)
                if cross <= a["hw"] + 1.0:
                    found.append(arm_vals(k, p))
        for v in (turn_vals(p) if turns else ()):
            found.append(v)
        return found[0] if len(found) == 1 else None

    def turn_vals(p):
        for cn in corners:
            if not cn["ok"]:
                continue
            A, B, c = arms[cn["i"]], arms[cn["j"]], cn["c"]
            wx, wy = p.x - c.x, p.y - c.y
            if wx * A["h"].x + wy * A["h"].y >= 0.0 or wx * B["h"].x + wy * B["h"].y >= 0.0:
                continue
            r = math.hypot(wx, wy)
            if r > cn["rmax"] or r < 1e-3:
                continue
            ux, uy = wx / r, wy / r
            a1 = math.acos(max(-1.0, min(1.0, ux * cn["na"].x + uy * cn["na"].y)))
            a2 = math.acos(max(-1.0, min(1.0, ux * cn["nb"].x + uy * cn["nb"].y)))
            fr = a1 / max(1e-6, a1 + a2)
            # each side's values on its corner line (they only depend on the distance along)
            la = (c.x * A["h"].x + c.y * A["h"].y) / A["aj"]
            lb = (c.x * B["h"].x + c.y * B["h"].y) / B["aj"]
            S_ = A["dS"] * la + (B["dS"] * lb - A["dS"] * la) * fr
            T_ = A["dT"] * la + (B["dT"] * lb - A["dT"] * la) * fr
            hw = A["hw"] + (B["hw"] - A["hw"]) * fr + cn["ea"] + (cn["eb"] - cn["ea"]) * fr
            yield (S_, T_, cn["sgn"] * (r - hw) + off[cn["i"]])
    return pin


def _hub_v2_grid_refine(pts, verts, tris, arms, fixed, wall_v, vals, psi, off, pin=None):
    """Re-solve the smooth fill on a REGULAR grid (a fan of thin triangles meeting in the middle
    gives a lopsided solve with a spike there) and read the mesh's values back from it."""
    h = HUB_V2_GRID
    xs = [p.x for p in verts]
    ys = [p.y for p in verts]
    x0, y0 = min(xs) - h, min(ys) - h
    NX = int((max(xs) - x0) / h) + 3
    NY = int((max(ys) - y0) / h) + 3
    tri2 = [(verts[a].x, verts[a].y, verts[b].x, verts[b].y, verts[c].x, verts[c].y) for a, b, c in tris]

    def inside(x, y):
        for (ax, ay, bx, by, cx, cy) in tri2:
            d1 = (x - bx) * (ay - by) - (ax - bx) * (y - by)
            d2 = (x - cx) * (by - cy) - (bx - cx) * (y - cy)
            d3 = (x - ax) * (cy - ay) - (cx - ax) * (y - ay)
            if not (((d1 < 0) or (d2 < 0) or (d3 < 0)) and ((d1 > 0) or (d2 > 0) or (d3 > 0))):
                return True
        return False
    cells = {}
    for i in range(NX):
        for j in range(NY):
            x, y = x0 + i * h, y0 + j * h
            if inside(x, y):
                cells[(i, j)] = [x, y]
    if not cells:
        return
    keys = list(cells)
    nbs = {c: [(c[0] + di, c[1] + dj) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if (c[0] + di, c[1] + dj) in cells] for c in keys}
    # boundary values: passage joints (all three), walls (cross axis only), from the mesh boundary
    bverts = [k for k in list(fixed) + list(wall_v)]
    fix_all, fix_v = {}, {}
    for c in keys:
        x, y = cells[c]
        for j, a in enumerate(arms):
            R, L = a["R"], a["L"]
            dx, dy = L.x - R.x, L.y - R.y
            t = max(0.0, min(1.0, ((x - R.x) * dx + (y - R.y) * dy) / max(1e-6, dx * dx + dy * dy)))
            if math.hypot(x - (R.x + dx * t), y - (R.y + dy * t)) < h * 0.75:
                fix_all[c] = [a["dS"], a["dT"], psi(a, V(x, y, 0)) + off[j]]
                break
        if c not in fix_all and pin is not None:
            pv = pin(V(x, y, 0.0))
            if pv is not None:
                fix_all[c] = list(pv)
        if c not in fix_all and len(nbs[c]) < 4 and bverts:
            k = min(bverts, key=lambda q: (pts[q].x - x) ** 2 + (pts[q].y - y) ** 2)
            fix_v[c] = fixed[k][2] if k in fixed else wall_v[k]
    # start each cell from the nearest mesh vertex
    g = {}
    for c in keys:
        if c in fix_all:
            g[c] = list(fix_all[c])
            continue
        x, y = cells[c]
        k = min(range(len(pts)), key=lambda q: (pts[q].x - x) ** 2 + (pts[q].y - y) ** 2)
        g[c] = list(vals[k])
        if c in fix_v:
            g[c][2] = fix_v[c]
    free = [c for c in keys if c not in fix_all and nbs[c]]
    w = 1.85
    for it in range(1500):
        delta = 0.0
        for c in free:
            ns = nbs[c]
            inv = 1.0 / len(ns)
            v = g[c]
            for comp in range(3):
                if comp == 2 and c in fix_v:
                    continue
                avg = sum(g[q][comp] for q in ns) * inv
                nv = v[comp] + w * (avg - v[comp])
                delta = max(delta, abs(nv - v[comp]) * (100.0 if comp == 1 else 1.0))
                v[comp] = nv
        if delta < 0.01:
            break
    _HUB_V2_ITERS.append(("grid", len(keys), it))
    # read the mesh values back (bilinear over the inside cells), keeping exact joint / wall values
    for k, p in enumerate(pts):
        if k in fixed:
            continue
        if pin is not None:
            pv = pin(p)
            if pv is not None:
                vals[k][0], vals[k][1], vals[k][2] = pv
                continue
        fi, fj = (p.x - x0) / h, (p.y - y0) / h
        i0, j0 = int(math.floor(fi)), int(math.floor(fj))
        acc, wsum = [0.0, 0.0, 0.0], 0.0
        for di in (0, 1):
            for dj in (0, 1):
                c = (i0 + di, j0 + dj)
                if c in g:
                    wt = (1 - abs(fi - c[0])) * (1 - abs(fj - c[1]))
                    for comp in range(3):
                        acc[comp] += g[c][comp] * wt
                    wsum += wt
        if wsum < 1e-6:
            c = min(keys, key=lambda q: (cells[q][0] - p.x) ** 2 + (cells[q][1] - p.y) ** 2)
            acc, wsum = list(g[c]), 1.0
        nv = [acc[0] / wsum, acc[1] / wsum, acc[2] / wsum]
        if k in wall_v:
            nv[2] = wall_v[k]
        vals[k][0], vals[k][1], vals[k][2] = nv


HUB_V2_THREE = "conformal"  # v2 3-way crossings: "conformal" = one smooth flow, ripples only ever
                          # scaled evenly (no streaks, no seams); "streams" = separate streams with
                          # seams (below); False/None = the plain smooth fill (streaky).
                          # "streams": 3-way crossings as separate streams (merge/split: each stream takes
                          # its own exact path - straight or the corner bend - to the shared passage,
                          # meeting in a seam; all in / all out: each passage's water runs straight
                          # in, the streams meeting in seams). False = one smooth fill (streaky).


HUB_V2_UNEVEN4 = True     # 4-way crossings where one passage feeds three (or three feed one) get the
                          # 3-way conformal flow too (the plain fill pinched the ripples into a
                          # dark streaky knot in the middle, SL_091); 2-in/2-out ones keep the fill


def _hub_v2_three(pts, ftris, arms, psi):
    """3-way crossings: per triangle (S, T, P) at its 3 corners, or None to use the smooth fill.
    One smooth field through a merge/split/collision has to stretch the ripples into streaks
    somewhere; separate exact streams don't (they meet in a seam, like real water)."""
    if len(arms) != 3:
        return None
    ins = [a["dT"] < 0 for a in arms]                 # water runs in along this passage
    ang = [a["ang"] for a in arms]

    def straight(a, p):                               # this passage's own water, carried on straight
        k = (p.x * a["h"].x + p.y * a["h"].y) / a["aj"]
        return [a["dS"] * k, a["dT"] * k, psi(a, p)]

    def angle_of(t):
        cx = sum(pts[q].x for q in t) / 3.0
        cy = sum(pts[q].y for q in t) / 3.0
        return math.atan2(cy, cx)

    def adist(x, y):
        return abs((x - y + math.pi) % (2 * math.pi) - math.pi)

    def collide():
        # each passage keeps its own water, carried on straight, up to the line halfway between
        # its direction and the next one's (streams colliding / parting)
        out = []
        for t in ftris:
            th = angle_of(t)
            j = min(range(3), key=lambda i: adist(th, ang[i]))
            out.append([straight(arms[j], pts[q]) for q in t])
        _HUB_V2_ITERS.append("collide")
        return out
    if sum(ins) in (0, 3):                            # all in (or all out)
        return collide()

    c = next(i for i in range(3) if sum(ins) == (1 if ins[i] else 2))   # the odd one out
    C = arms[c]
    fields = {}
    for x in range(3):
        if x == c:
            continue
        X = arms[x]
        gap = (C["ang"] - X["ang"]) % (2 * math.pi)
        vals = [None] * len(pts)
        if abs(gap - math.pi) < math.radians(3):
            # straight through: S, T run evenly from X's mouth to C's; P is X's (= C's) cross axis
            sx, sc = X["aj"], C["aj"]
            dP = psi(C, V(0, 0, 0)) - psi(X, V(0, 0, 0))
            if X["right"].x * C["right"].x + X["right"].y * C["right"].y < 0:
                return collide()                      # cross axes run opposite ways
            shift = round(dP / HUB_V2_TILE) * HUB_V2_TILE
            for k, p in enumerate(pts):
                f = (sx - (p.x * X["h"].x + p.y * X["h"].y)) / max(1.0, sx + sc)
                vals[k] = [X["dS"] + (C["dS"] - X["dS"]) * f, X["dT"] + (C["dT"] - X["dT"]) * f,
                           (psi(X, p) + shift) * (1.0 - f) + psi(C, p) * f]
        else:
            if not _hub_v2_bend(pts, [X, C], {}, vals, psi, [0.0, 0.0]):
                return collide()                      # (its cross axis is mirrored vs the flow)
        fields[x] = vals
    xs = sorted(fields, key=lambda i: (ang[i] - ang[c]) % (2 * math.pi))
    r1 = (ang[xs[0]] - ang[c]) % (2 * math.pi)
    r2 = (ang[xs[1]] - ang[c]) % (2 * math.pi)
    out = []
    for t in ftris:
        rel = (angle_of(t) - ang[c]) % (2 * math.pi)
        x = xs[0] if rel < 0.5 * (r1 + r2) else xs[1]
        out.append([list(fields[x][q]) for q in t])
    _HUB_V2_ITERS.append("streams")
    return out


def _hub_v2_conformal(pts, ftris, arms, fixed, vals):
    """3-way crossings, one smooth flow without streaks: distance-along-the-flow (S) and the cross
    axis (P) solved TOGETHER so the ripples are only ever scaled evenly, never squashed one way
    (a least-squares conformal map, mouths fixed, walls free). Two passages' worth of water into
    one then just shows as ripples a little bigger or smaller (slower / faster water), spread over
    the crossing, instead of streaks. Travel time follows S. Updates vals in place; False when a
    passage's cross axis runs mirrored against the flow (can't be one smooth field there)."""
    hands = set()
    for a in arms:
        fx, fy = (a["h"].x, a["h"].y) if a["dS"] > 0 else (-a["h"].x, -a["h"].y)
        hands.add(1.0 if a["right"].x * -fy + a["right"].y * fx > 0 else -1.0)
    if len(hands) != 1:
        return False
    sg = hands.pop()
    n = len(pts)
    # least squares: per triangle sqrt(area) * (grad P - sg * rot90(grad S)) = 0
    N = [dict() for _ in range(2 * n)]          # normal matrix rows, x = [S0..Sn-1, P0..Pn-1]
    for (i0, i1, i2) in ftris:
        if len({i0, i1, i2}) < 3:
            continue
        a, b, c = pts[i0], pts[i1], pts[i2]
        e1x, e1y, e2x, e2y = b.x - a.x, b.y - a.y, c.x - a.x, c.y - a.y
        det = e1x * e2y - e2x * e1y
        if abs(det) < 1e-9:
            continue
        # gradients of the barycentric weights of b and c (a's = minus their sum)
        gb = (e2y / det, -e2x / det)
        gc = (-e1y / det, e1x / det)
        g = ((-gb[0] - gc[0], -gb[1] - gc[1]), gb, gc)
        w = abs(det) * 0.5
        ids = (i0, i1, i2)
        for d in range(2):
            row = {}
            for k in range(3):
                # rot90(grad S) = (-dS/dy, dS/dx)
                rs = -g[k][1] if d == 0 else g[k][0]
                row[n + ids[k]] = row.get(n + ids[k], 0.0) + g[k][d]
                row[ids[k]] = row.get(ids[k], 0.0) - sg * rs
            for p_, vp in row.items():
                Np = N[p_]
                for q_, vq in row.items():
                    Np[q_] = Np.get(q_, 0.0) + w * vp * vq
    x = [vals[k][0] for k in range(n)] + [vals[k][2] for k in range(n)]
    fixed_idx = set()
    for k, v in fixed.items():
        x[k], x[n + k] = v[0], v[2]
        fixed_idx.update((k, n + k))
    free = [i for i in range(2 * n) if i not in fixed_idx and N[i]]
    pos = {i: j for j, i in enumerate(free)}
    # N_ff y = -N_fc x_c, solved by preconditioned conjugate gradients from the smooth fill
    rhs = []
    for i in free:
        rhs.append(-sum(v * x[q] for q, v in N[i].items() if q not in pos))
    A = [[(pos[q], v) for q, v in N[i].items() if q in pos] for i in free]
    diag = [max(1e-12, N[i].get(i, 0.0)) for i in free]
    y = [x[i] for i in free]

    def mul(v):
        return [sum(c * v[j] for j, c in row) for row in A]
    Ay = mul(y)
    r = [rhs[i] - Ay[i] for i in range(len(y))]
    z = [r[i] / diag[i] for i in range(len(y))]
    p = list(z)
    rz = sum(r[i] * z[i] for i in range(len(y)))
    r0 = math.sqrt(sum(v * v for v in rhs)) or 1.0
    it = 0
    for it in range(4000):
        if math.sqrt(sum(v * v for v in r)) < 1e-9 * r0:
            break
        Ap = mul(p)
        pAp = sum(p[i] * Ap[i] for i in range(len(p)))
        if abs(pAp) < 1e-30:
            break
        al = rz / pAp
        for i in range(len(y)):
            y[i] += al * p[i]
            r[i] -= al * Ap[i]
        z = [r[i] / diag[i] for i in range(len(y))]
        rz2 = sum(r[i] * z[i] for i in range(len(y)))
        be = rz2 / rz
        rz = rz2
        p = [z[i] + be * p[i] for i in range(len(y))]
    for j, i in enumerate(free):
        x[i] = y[j]
    vbar = sum(abs(a["dS"]) / max(1e-3, abs(a["dT"])) for a in arms) / len(arms)
    for k in range(n):
        if k in fixed:
            continue
        S_ = x[k]
        vals[k] = [S_, vals[k][1] + (S_ - vals[k][0]) / vbar, x[n + k]]
    _HUB_V2_ITERS.append(("conformal", it))
    return True


def _hub_water_v2(node, verts, tris, arms):
    """v2 crossing water: the same outline, finely subdivided, with the flow values (distance,
    travel time, cross-channel axis) spread smoothly across it from where each passage's water
    starts (a smooth 'harmonic' fill, like a soap film stretched between the passage ends).
    The ripples then bend through the crossing from the inflows to the outflows with no seams,
    no fading and no streaks: each passage's values are matched exactly at its joint."""
    M = max(1, int(HUB_V2_SUBDIV))
    keys, pts, ftris = {}, [], []

    def pid(p):
        k = (int(round(p.x * 10.0)), int(round(p.y * 10.0)))
        if k not in keys:
            keys[k] = len(pts)
            pts.append(p)
        return keys[k]
    for (i0, i1, i2) in tris:
        p0, p1, p2 = verts[i0], verts[i1], verts[i2]
        grid = {}
        for i in range(M + 1):
            for j in range(M + 1 - i):
                q = p0 + (p1 - p0) * (float(i) / M) + (p2 - p0) * (float(j) / M)
                grid[(i, j)] = pid(q)
        for i in range(M):
            for j in range(M - i):
                ftris.append((grid[(i, j)], grid[(i + 1, j)], grid[(i, j + 1)]))
                if i + j < M - 1:
                    ftris.append((grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)]))
    nb = [set() for _ in pts]
    for t in ftris:
        for x in range(3):
            a_, b_ = t[x], t[(x + 1) % 3]
            if a_ != b_:
                nb[a_].add(b_)
                nb[b_].add(a_)

    # whole-tile shifts of each arm's cross axis so neighbouring arms' wall values line up
    def psi(a, p):
        return (p.x - a["Pl"].x) * a["right"].x + (p.y - a["Pl"].y) * a["right"].y
    n = len(arms)
    tvals = _hub_v2_three(pts, ftris, arms, psi) if (HUB_V2_THREE == "streams" and n == 3) else None
    if tvals is not None:
        return _hub_v2_write(node, pts, ftris, tvals)
    off = [0.0] * n
    # go round from just after the widest gap between arms, so whatever doesn't add up ends on
    # the longest wall (spread thin) rather than somewhere cramped
    gaps = [((arms[(i + 1) % n]["ang"] - arms[i]["ang"]) % (2 * math.pi)) if n > 1 else 0.0 for i in range(n)]
    g = max(range(n), key=lambda i: gaps[i]) if n else 0
    order = [(g + 1 + i) % n for i in range(n)]
    for a_prev, a_here in zip(order, order[1:]):
        prev_left = psi(arms[a_prev], arms[a_prev]["L"]) + off[a_prev]
        here_right = psi(arms[a_here], arms[a_here]["R"])
        off[a_here] = round((prev_left - here_right) / HUB_V2_TILE) * HUB_V2_TILE

    # fixed values on every passage joint (the segment from its R to its L corner)
    fixed, fixed_arm = {}, {}
    for j, a in enumerate(arms):
        R, L = a["R"], a["L"]
        dx, dy = L.x - R.x, L.y - R.y
        ln2 = dx * dx + dy * dy
        for k, p in enumerate(pts):
            t = ((p.x - R.x) * dx + (p.y - R.y) * dy) / max(1e-6, ln2)
            if -1e-3 <= t <= 1.001:
                cx, cy = R.x + dx * t, R.y + dy * t
                if math.hypot(p.x - cx, p.y - cy) < 0.5:
                    fixed[k] = (a["dS"], a["dT"], psi(a, p) + off[j])
                    fixed_arm[k] = j
    # the walls carry the cross axis too (in real water a wall is a flow line): along each wall
    # it runs evenly from one passage's edge value to the next passage's, so the ripples span
    # the whole width of the crossing instead of smearing
    ecount = {}
    for t in ftris:
        for x in range(3):
            e = tuple(sorted((t[x], t[(x + 1) % 3])))
            if e[0] != e[1]:
                ecount[e] = ecount.get(e, 0) + 1
    bn = {}
    for e, c in ecount.items():
        if c == 1:
            bn.setdefault(e[0], []).append(e[1])
            bn.setdefault(e[1], []).append(e[0])
    # 3+ passages: each passage's straight run keeps its own exact values right up to where it
    # meets the others (v4 also turns round each corner); only the meeting area is filled
    pin = None
    if len(arms) >= 3 and HUB_FLOW_VERSION in (2, 4, 5):
        pin = _hub_v2_corner_pin(arms, psi, off, turns=(HUB_FLOW_VERSION == 4))
    anchor = {k: v[2] for k, v in fixed.items()}
    if pin is not None:
        for k in bn:
            if k not in anchor:
                pv = pin(pts[k])
                if pv is not None:
                    anchor[k] = pv[2]
    wall_v = {}
    if bn and fixed:
        start = next(k for k in bn if k in fixed)
        loop, prev, cur = [start], None, start
        for _ in range(len(bn) + 1):
            nxt = [q for q in bn[cur] if q != prev]
            if not nxt or nxt[0] == start:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
        L = len(loop)
        fixed_pos = [i for i, k in enumerate(loop) if k in anchor]
        for fi, i0 in enumerate(fixed_pos):
            i1 = fixed_pos[(fi + 1) % len(fixed_pos)]
            span = (i1 - i0) % L
            if span <= 1:
                continue
            seg = [loop[(i0 + s_) % L] for s_ in range(span + 1)]
            cum = [0.0]
            for q in range(1, len(seg)):
                pa, pb = pts[seg[q - 1]], pts[seg[q]]
                cum.append(cum[-1] + math.hypot(pb.x - pa.x, pb.y - pa.y))
            va, vb = anchor[seg[0]], anchor[seg[-1]]
            for q in range(1, len(seg) - 1):
                wall_v[seg[q]] = va + (vb - va) * cum[q] / max(1e-6, cum[-1])

    # start from the nearest joint's values, then relax (over-relaxed Gauss-Seidel)
    vals = []
    for k, p in enumerate(pts):
        if k in fixed:
            vals.append(list(fixed[k]))
            continue
        best = min(range(n), key=lambda j: (p.x - arms[j]["Pl"].x) ** 2 + (p.y - arms[j]["Pl"].y) ** 2)
        a = arms[best]
        vals.append([a["dS"] * 0.5, a["dT"] * 0.5, wall_v.get(k, psi(a, p) + off[best])])
    free = [k for k in range(len(pts)) if k not in fixed and nb[k]]
    nbl = [list(x) for x in nb]
    w = 1.7
    for it in range(600):
        delta = 0.0
        for k in free:
            ns = nbl[k]
            inv = 1.0 / len(ns)
            v = vals[k]
            for c in range(3):
                if c == 2 and k in wall_v:
                    continue
                avg = sum(vals[q][c] for q in ns) * inv
                nv = v[c] + w * (avg - v[c])
                delta = max(delta, abs(nv - v[c]) * (100.0 if c == 1 else 1.0))   # time: 0.01 s ~ 1 cm
                v[c] = nv
        if delta < 0.01:
            break
    _HUB_V2_ITERS.append(it)
    _hub_v2_grid_refine(pts, verts, tris, arms, fixed, wall_v, vals, psi, off, pin)
    if _hub_v2_bend(pts, arms, fixed, vals, psi, [0.0] * len(arms)):
        for k, j in fixed_arm.items():      # the turn keeps both mouths on the same tile
            fixed[k] = (fixed[k][0], fixed[k][1], psi(arms[j], pts[k]))
            vals[k][2] = fixed[k][2]
    uneven4 = n == 4 and HUB_V2_UNEVEN4 and sum(1 for a in arms if a["dS"] > 0) in (1, 3)
    if HUB_V2_THREE == "conformal" and (n == 3 or uneven4):
        if not _hub_v2_conformal(pts, ftris, arms, fixed, vals):
            tv = _hub_v2_three(pts, ftris, arms, psi)       # mirrored passage: separate streams
            if tv is not None:
                return _hub_v2_write(node, pts, ftris, tv)
    qual = _hub_v2_quality(pts, ftris, vals, fixed) if HUB_V2_CALM else [1.0] * len(pts)
    tvals = [[(vals[k][0], vals[k][1], vals[k][2], qual[k]) for k in t] for t in ftris]
    return _hub_v2_write(node, pts, ftris, tvals)


def _hub_v2_write(node, pts, ftris, tvals):
    """Bakes the crossing water: tvals = per triangle, (S, T, P[, weight]) at each corner."""
    m = _new_mesh()
    ids = []
    for p in pts:
        r = gs("add_vertex_to_mesh")(m, p, False)
        ids.append(r[1] if isinstance(r, tuple) else r)
    tids = []
    for t in ftris:
        if len(set(t)) < 3:
            tids.append(None)
            continue
        r = gs("add_triangle_to_mesh")(m, unreal.IntVector(ids[t[0]], ids[t[1]], ids[t[2]]), 0, False)
        tids.append(r[1] if isinstance(r, tuple) else r)
    _finish_mesh(m, normals=True)
    _ensure_uv_sets(m, 4)
    for tv, tid in zip(tvals, tids):
        if tid is None:
            continue
        _set_uv_triangle(m, 2, tid, [(c[0], c[1]) for c in tv])
        _set_uv_triangle(m, 3, tid, [(c[2], c[3] if len(c) > 3 else 1.0) for c in tv])
    sm = _bake(m, "%s/SM_SewerHubWaterV%d%s_%s" % (GENERATED_FOLDER, HUB_FLOW_VERSION, HUB_ASSET_SUFFIX, _safe(node.get_actor_label())),
               WATER_MATERIAL)
    try:
        ses = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        bs = ses.get_lod_build_settings(sm, 0)
        bs.set_editor_property("use_full_precision_u_vs", True)
        bs.set_editor_property("generate_lightmap_u_vs", False)
        ses.set_lod_build_settings(sm, 0, bs)
        unreal.EditorAssetLibrary.save_loaded_asset(sm, False)
    except Exception as ex:  # noqa
        unreal.log_warning("Sewer: hub water build settings not set (%s)" % ex)
    return sm


def _hub_drift(conns):
    """Direction the calm water in a crossing's middle drifts: the sum of where the water goes
    (out along the arms it leaves by, in from the ones it arrives by)."""
    sx = sy = 0.0
    for c in conns:
        h = V(c["h"].x, c["h"].y, 0.0).normal()
        if c["pitch"] < -LEVEL_EPS_DEG:
            out = True
        elif c["pitch"] > LEVEL_EPS_DEG:
            out = False
        else:
            out = not c.get("mirror")
        sx += h.x if out else -h.x
        sy += h.y if out else -h.y
    ln = math.hypot(sx, sy)
    if ln < 1e-3:
        return 0.6, 0.8
    return sx / ln, sy / ln


def _flow_profile(edge):
    """(total length S, speed at s) for an edge, s measured along the flow from its upstream end."""
    S = max(1.0, edge["lead_a"] + max(edge["length"], 0.0) + edge["lead_b"])
    vm = FLOW_SPEED_LEVEL + abs(edge.get("pitch", 0.0)) * FLOW_SPEED_PER_DEG
    ease = min(FLOW_EASE, S * 0.5)

    def v(s):
        k = max(0.0, min(1.0, s / ease, (S - s) / ease))
        return FLOW_SPEED_NODE + (vm - FLOW_SPEED_NODE) * k
    return S, v


def _flow_time(v, s0, s1, step=10.0):
    """Seconds the water takes from s0 to s1 (s1 >= s0)."""
    t, s = 0.0, s0
    while s < s1 - 1e-6:
        ds = min(step, s1 - s)
        t += ds / max(1.0, 0.5 * (v(s) + v(s + ds)))
        s += ds
    return t


def _flow_downhill_ab(edge):
    """True when the water runs from node A to node B (downhill, or A->B when level)."""
    return not (edge.get("pitch", 0.0) > LEVEL_EPS_DEG)


_FLOW_FIELD = {"nodes": {}, "edges": {}}


def _flow_field(edges):
    """Two smooth values over the whole network, continuous through every crossing:
    S = distance along the flow, T = travel time of the water (from the speed profile).
    Each node gets one value of each (least squares over its passages, so loops fit as well as
    they can); along a passage they run between its two nodes following its speed profile.
    The material moves the ripples by T (fast water stretches them, slow water bunches them)."""
    info = {}
    adj = {}
    for k, e in enumerate(edges):
        d = e["dir"]
        xa = (e["pa"] - e["bend_a"]).dot(d)
        xb = (e["pb"] - e["bend_a"]).dot(d)
        S, v = _flow_profile(e)
        ab = _flow_downhill_ab(e)

        def speed_x(x, S=S, v=v, ab=ab):
            s = x if ab else S - x
            return v(max(0.0, min(S, s)))
        n = max(2, int((xb - xa) / 10.0) + 1)
        xs, tr = [xa], [0.0]
        for i in range(1, n + 1):
            x0, x1 = xa + (xb - xa) * (i - 1) / n, xa + (xb - xa) * i / n
            tr.append(tr[-1] + (x1 - x0) / max(1.0, 0.5 * (speed_x(x0) + speed_x(x1))))
            xs.append(x1)
        sign = 1.0 if ab else -1.0
        info[k] = {"xs": xs, "tr": tr, "speed": speed_x, "dS": sign * (xb - xa), "dT": sign * tr[-1], "sign": sign,
                   "bend_a": e["bend_a"], "dir": d, "a": e["a"], "b": e["b"]}
        w = 1.0 / max(1.0, tr[-1]) ** 2
        adj.setdefault(e["a"], []).append((e["b"], k, -1.0, w))   # value_a = value_b - d
        adj.setdefault(e["b"], []).append((e["a"], k, 1.0, w))    # value_b = value_a + d
    # start from a walk outwards, then relax (Gauss-Seidel) so loops share their misfit
    val = {}
    for start in sorted(adj):
        if start in val:
            continue
        val[start] = (0.0, 0.0)
        stack = [start]
        while stack:
            n0 = stack.pop()
            for n1, k, sg, w in adj[n0]:
                if n1 not in val:
                    val[n1] = (val[n0][0] - sg * info[k]["dS"], val[n0][1] - sg * info[k]["dT"])
                    stack.append(n1)
    if FLOW_LOOP_WRAP:
        _read_flow_material()
    for _ in range(0 if FLOW_LOOP_WRAP else 400):
        moved = 0.0
        for n0 in adj:
            ws = ss = ts = 0.0
            for n1, k, sg, w in adj[n0]:
                ss += w * (val[n1][0] + sg * info[k]["dS"])
                ts += w * (val[n1][1] + sg * info[k]["dT"])
                ws += w
            new = (ss / ws, ts / ws)
            moved = max(moved, abs(new[1] - val[n0][1]))
            val[n0] = new
        if moved < 1e-4:
            break
    flipped = 0
    for k, ed in info.items():
        ed["SA"], ed["TA"] = val[ed["a"]]
        SBn, TBn = val[ed["b"]]
        ed["SBn"], ed["TBn"] = SBn, TBn               # the node's own values
        if FLOW_LOOP_WRAP:
            # this passage's own far-end values: exact, apart from whole ripple repeats (a loop that
            # doesn't add up is closed here, invisibly); what's left over (under half a repeat) is
            # spread along the passage
            P = FLOW_WRAP_TILE / max(1e-3, (1.0 - FLOW_WRAP_BALANCE) * FLOW_WRAP_VREF)   # s per repeat
            Q = FLOW_WRAP_TILE / max(1e-3, FLOW_WRAP_BALANCE)                            # cm per repeat
            kt = round(((TBn - ed["TA"]) - ed["dT"]) / P)
            ks = round(((SBn - ed["SA"]) - ed["dS"]) / Q)
            ed["SB"], ed["TB"] = SBn - ks * Q, TBn - kt * P
        else:
            ed["SB"], ed["TB"] = SBn, TBn
        if (ed["TB"] - ed["TA"]) * ed["dT"] <= 0.0:
            flipped += 1
    if flipped:
        unreal.log_warning("Sewer: water on %d passage(s) runs against its slope (a loop that flows round "
                           "in a circle can't be fitted)" % flipped)
    _flow_vsigns(edges, info)
    _FLOW_FIELD["nodes"] = val
    _FLOW_FIELD["edges"] = info
    return _FLOW_FIELD


def _flow_vsigns(edges, info):
    """Which way each passage's cross axis runs (the ripple texture's 'across' direction; it is
    just a mirror, the texture looks the same). It has to agree between the two passages of every
    two-way crossing (turns and straights), or the crossing water would twist; elsewhere it follows
    the flow. Set by walking along chains of two-way crossings."""
    for ed in info.values():
        ed["vsign"] = ed["sign"]
    at = {}
    for k, e in enumerate(edges):
        if e.get("cross_a"):
            at.setdefault(e["a"], []).append((k, 0))
        if e.get("cross_b"):
            at.setdefault(e["b"], []).append((k, 1))
    links = {}
    for node, lst in at.items():
        if len(lst) != 2:
            continue
        arms = []
        for k, side in lst:
            d = edges[k]["dir"]
            h = V(d.x, d.y, 0.0).normal() * (1.0 if side == 0 else -1.0)      # out of this node
            r = unreal.MathLibrary.make_rot_from_x(d).get_right_vector()
            arms.append((math.atan2(h.y, h.x), k, h, V(r.x, r.y, 0.0)))
        arms.sort()
        (a0, kA, hA, rA), (a1, kB, hB, rB) = arms
        if (a1 - a0) % (2 * math.pi) > math.pi + 1e-6:
            (a0, kA, hA, rA), (a1, kB, hB, rB) = arms[1], arms[0]
        nlA, nlB = V(-hA.y, hA.x, 0.0), V(-hB.y, hB.x, 0.0)
        ra = 1.0 if (-nlA.x * rA.x - nlA.y * rA.y) > 0 else -1.0
        rb = 1.0 if (nlB.x * rB.x + nlB.y * rB.y) > 0 else -1.0
        rel = ra * rb                          # vsign_B must be vsign_A * rel
        links.setdefault(kA, []).append((kB, rel))
        links.setdefault(kB, []).append((kA, rel))
    seen, clash = set(), 0
    for start in links:
        if start in seen:
            continue
        seen.add(start)
        stack = [start]
        while stack:
            k = stack.pop()
            for k2, rel in links[k]:
                want = info[k]["vsign"] * rel
                if k2 in seen:
                    if info[k2]["vsign"] != want:
                        clash += 1
                    continue
                info[k2]["vsign"] = want
                seen.add(k2)
                stack.append(k2)
    if clash:
        unreal.log_warning("Sewer: %d two-way crossing(s) in closed loops can't line their ripples up" % (clash // 2))
    if VSIGN_CHAIN_FLIPS:
        _flow_vsign_chains(edges, info, at, links)


VSIGN_CHAIN_FLIPS = True    # mirror whole chains of passages so every 3+ way crossing's passages all
                            # carry their cross axis the same way round relative to the flow


def _flow_vsign_chains(edges, info, at, links):
    """A chain of passages joined through two-way crossings must keep its signs relative to each
    other, but the whole chain can be mirrored (the texture looks the same). Pick the mirrors so
    that at every crossing of 3+ passages they all agree relative to the flow - else one passage's
    ripples run mirrored there and no smooth crossing water can join it."""
    comp = {}
    for k in range(len(edges)):
        if k in comp:
            continue
        comp[k] = k
        stack = [k]
        while stack:
            x = stack.pop()
            for y, _ in links.get(x, []):
                if y not in comp:
                    comp[y] = k
                    stack.append(y)

    def hand(k):
        return info[k]["vsign"] * info[k]["sign"]
    cons = {}
    for node, lst in at.items():
        if len(lst) < 3:
            continue
        ks = [k for k, _ in lst]
        for b in ks[1:]:
            a = ks[0]
            rel = hand(a) * hand(b)
            cons.setdefault(comp[a], []).append((comp[b], rel))
            cons.setdefault(comp[b], []).append((comp[a], rel))
    f, clash = {}, 0
    for start in sorted(cons, key=lambda c: -len(cons[c])):
        if start in f:
            continue
        f[start] = 1.0
        stack = [start]
        while stack:
            c = stack.pop()
            for c2, rel in cons[c]:
                want = f[c] * rel
                if c2 in f:
                    clash += f[c2] != want
                    continue
                f[c2] = want
                stack.append(c2)
    flipped = 0
    for k in info:
        if f.get(comp.get(k, k), 1.0) < 0:
            info[k]["vsign"] = -info[k]["vsign"]
            flipped += 1
    if clash:
        unreal.log_warning("Sewer: %d crossing link(s) can't all line their ripples up" % (clash // 2))
    _HUB_V2_ITERS.append(("vsign chains flipped", flipped, clash // 2))


def _flow_field_at(ed, x):
    """(S, T) at distance x along the edge (from bend_a)."""
    xs, tr = ed["xs"], ed["tr"]
    if x <= xs[0]:
        f = 0.0
    elif x >= xs[-1]:
        f = 1.0
    else:
        span = xs[-1] - xs[0]
        i = min(len(xs) - 2, int((x - xs[0]) / span * (len(xs) - 1)))
        while i > 0 and xs[i] > x:
            i -= 1
        while i < len(xs) - 2 and xs[i + 1] < x:
            i += 1
        u = (x - xs[i]) / max(1e-6, xs[i + 1] - xs[i])
        f = (tr[i] + (tr[i + 1] - tr[i]) * u) / max(1e-6, tr[-1])
    g = (x - xs[0]) / max(1e-6, xs[-1] - xs[0])
    g = max(0.0, min(1.0, g))
    return ed["SA"] + (ed["SB"] - ed["SA"]) * g, ed["TA"] + (ed["TB"] - ed["TA"]) * f


_FLOW_CACHE = {}   # (unused now; kept so older calls don't break)


def _flow_instance(eid, sa, length):
    """Custom data for a water instance covering [sa, sa+length] along the edge (A->B):
    S and T at its local x = 0 and far end, the speed at both ends (shape of T in between), mode 1."""
    ed = _FLOW_FIELD["edges"][eid]
    S0, T0 = _flow_field_at(ed, sa)
    S1, T1 = _flow_field_at(ed, sa + length)
    # v2: mode carries the cross-axis direction (follows the flow, like a real stream function)
    mode = ed["vsign"] if HUB_FLOW_VERSION in (2, 4, 5) else 1.0
    return (S0, S1, T0, T1, ed["speed"](sa), ed["speed"](sa + length), mode)


_LAST_NET = {}


def network_actors():
    """The network actor(s) of the last build."""
    net = _LAST_NET.get("net")
    return list(net.actors.values()) if isinstance(net, _NetGrid) else ([net] if net else [])


def _rebuild_network(edges, nodes, per_node=None):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in _actors():
        lab = a.get_actor_label()
        if lab == NETWORK_LABEL or lab.startswith(NETWORK_LABEL + "_"):
            eas.destroy_actor(a)
    if NETWORK_SPLIT:
        net = _NetGrid()
    else:
        net = eas.spawn_actor_from_class(unreal.StaticMeshActor, V(0, 0, 0), unreal.Rotator(0, 0, 0))
        net.set_actor_label(NETWORK_LABEL)
    _LAST_NET["net"] = net

    count = 0
    _FLOW_CACHE.clear()
    _flow_field(edges)
    eids = {id(e): k for k, e in enumerate(edges)}
    for ptype, pcfg in PASSAGE_TYPES.items():
        mine = [e for e in edges if e["ptype"] == ptype]
        if not mine:
            continue
        sm = unreal.EditorAssetLibrary.load_asset(pcfg["mesh"])
        if sm is None:
            raise RuntimeError("Passage mesh not found: " + pcfg["mesh"])
        seg_len = pcfg["segment_length"]
        cells = _Cells(net, "HISM_" + ptype, sm)
        water_mat = unreal.EditorAssetLibrary.load_asset(WATER_MATERIAL) if WATER_MATERIAL else None
        water_cells = _Cells(net, "HISM_Water_" + ptype, _water_asset(ptype), FLOW_CUSTOM, water_mat) \
            if pcfg.get("water_half_width") else None
        under_mat = unreal.EditorAssetLibrary.load_asset(WATER_UNDER_MATERIAL) if WATER_UNDER_MATERIAL else None
        under_cells = _Cells(net, "HISM_WaterUnder_" + ptype, _water_asset(ptype), FLOW_CUSTOM, under_mat) \
            if (water_cells and under_mat) else None
        for e in mine:
            segs = _segment_transforms(e)
            for k, t in enumerate(segs):
                where = _mid(t, seg_len)
                _add_instance(cells.get(where), t)
                if water_cells:
                    wt = _longer(t, WATER_OVERLAP, seg_len)
                    sa = (wt.translation - e["bend_a"]).dot(e["dir"])
                    fd = _flow_instance(eids[id(e)], sa, wt.scale3d.x * seg_len)
                    _add_water(water_cells.get(where), _raised(wt), fd)
                    if under_cells:
                        _add_water(under_cells.get(where), wt, fd)
                count += 1
            if water_cells:
                for t, fade in _lead_water_transforms(e):
                    if t.scale3d.x > 0.001:
                        wt = _longer(t, WATER_OVERLAP, seg_len)
                        sa = (wt.translation - e["bend_a"]).dot(e["dir"])
                        fd = _flow_instance(eids[id(e)], sa, wt.scale3d.x * seg_len)
                        _add_water(water_cells.get(_mid(t, seg_len)), _raised(wt), fd)
                        if under_cells:
                            _add_water(under_cells.get(_mid(t, seg_len)), wt, fd)

    for n in nodes:
        if not _is_crossing(_node_type(n)) or per_node is None:
            continue
        conns = per_node.get(n.get_path_name(), [])
        if not conns:
            continue
        hub_actor = _net_actor(net, n.get_actor_location())
        comp = _add_hism(hub_actor, "HISM_HubWater_" + _safe(n.get_actor_label()), _hub_water_asset(n, conns))
        _water_collision(comp)
        try:
            comp.set_editor_property("num_custom_data_floats", FLOW_CUSTOM)
        except Exception:
            pass
        Sn, Tn = _FLOW_FIELD["nodes"].get(n.get_path_name(), (0.0, 0.0))
        dx, dy = _hub_drift(conns)
        hub_xf = unreal.Transform(location=n.get_actor_location())
        _add_water(comp, _raised(hub_xf), (Sn, Sn, Tn, Tn, dx, dy, 0.0))
        if WATER_UNDER_MATERIAL:
            under = _add_hism(hub_actor, "HISM_HubWaterUnder_" + _safe(n.get_actor_label()),
                              comp.get_editor_property("static_mesh"))
            under.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            under.set_material(0, unreal.EditorAssetLibrary.load_asset(WATER_UNDER_MATERIAL))
            _add_instance(under, hub_xf)

    for ptype in PASSAGE_TYPES:
        caps = []
        if not any(e["ptype"] == ptype and (e["cap_a"] or e["cap_b"]) for e in edges):
            continue
        # modelled end pieces may not start at their pivot: put their inner face (lowest X)
        # exactly on the run end
        cap_sm = _cap_asset(ptype)
        front = PASSAGE_TYPES[ptype].get("end_front", "min") if PASSAGE_TYPES[ptype].get("end_mesh") else "min"
        try:
            box = cap_sm.get_bounding_box()
            face_x = box.max.x if front == "max" else box.min.x
        except Exception:
            face_x = 0.0
        # the wall's front face (the side at face_x, facing into the passage) goes exactly on
        # the run end; the wall body extends away from the passage
        flip = -1.0 if front == "max" else 1.0
        for e in edges:
            if e["ptype"] != ptype:
                continue
            for flag, end_pt, out_dir in (("cap_b", e["end"], e["dir"]), ("cap_a", e["start"], e["dir"] * -1.0)):
                if not e[flag]:
                    continue
                x_axis = out_dir * flip            # local +X in world
                caps.append(unreal.Transform(location=end_pt - x_axis * face_x,
                                             rotation=unreal.MathLibrary.make_rot_from_x(x_axis)))
        if caps:
            cap_cells = _Cells(net, "HISM_Cap_" + ptype, cap_sm)
            for t in caps:
                _add_instance(cap_cells.get(t.translation), t)
    return count


# =============================================================================
# Entry points
# =============================================================================

DEFINITIVE_FOLDER = "/Game/Sewers/Meshes/Definitive"
DEFINITIVE_MATERIAL = "/Game/Level/Sewers/M_Master_Sewers_Inst"
DEFINITIVE = {   # (table, key, field) -> definitive kit piece (used whenever it has been imported)
    ("P", "P12", "mesh"): "Passage12Defo", ("P", "P12", "end_mesh"): "Passage12EndDefo",
    ("P", "P20", "mesh"): "Passage20Defo", ("P", "P20", "end_mesh"): "Passage20EndDefo",
    ("N", "Junction", "shell_mesh"): "JunctionDefo", ("N", "Junction", "base_mesh"): "JunctionBaseDefo",
    ("N", "Shaft", "shell_mesh"): "ShaftDefo", ("N", "Shaft", "base_mesh"): "ShaftBaseDefo",
}


def use_definitive():
    """Point the kit at the definitive meshes (sewer_definitive_import.py) where they exist."""
    used = []
    for (tab, key, field), name in DEFINITIVE.items():
        path = DEFINITIVE_FOLDER + "/" + name
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            (PASSAGE_TYPES if tab == "P" else NODE_TYPES)[key][field] = path
            used.append(name)
    _UV_TABLES.clear()
    _OUTER.clear()
    global NODE_MATERIAL
    if used and unreal.EditorAssetLibrary.does_asset_exist(DEFINITIVE_MATERIAL):
        NODE_MATERIAL = DEFINITIVE_MATERIAL         # generated caps match the kit
    if used:
        unreal.log("Sewer: definitive kit: " + ", ".join(used))
    return used


def build(only_selected=False):
    """Build the whole sewer. only_selected=True rebakes just the selected nodes' meshes."""
    use_definitive()
    unreal.EditorAssetLibrary.make_directory(GENERATED_FOLDER)
    nodes = [a for a in _actors() if _is_node(a)]
    if not nodes:
        unreal.EditorDialog.show_message("Sewer Builder", "No %s actors in the level." % NODE_CLASS_NAME,
                                         unreal.AppMsgType.OK)
        return

    warnings = []
    _UV_TABLES.clear()
    _OUTER.clear()   # re-read passage UVs (they may have been re-imported)
    edges, per_node = _gather(nodes, warnings)
    selected = set(a.get_path_name() for a in
                   unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors())
    to_bake = [n for n in nodes if (not only_selected or n.get_path_name() in selected)
               and _node_type(n) in NODE_TYPES]

    with unreal.ScopedEditorTransaction("Build Sewer"):
        with unreal.ScopedSlowTask(len(to_bake) + 1, "Building sewer...") as task:
            task.make_dialog(True)
            for n in to_bake:
                if task.should_cancel():
                    break
                task.enter_progress_frame(1, "Node " + n.get_actor_label())
                conns = per_node.get(n.get_path_name(), [])
                _check_angles(n, conns, warnings)
                if _is_end(_node_type(n)):
                    # End nodes are just markers; the cap lives on the network HISM.
                    comp = n.get_component_by_class(unreal.StaticMeshComponent)
                    if comp:
                        comp.modify()
                        comp.set_static_mesh(None)
                    continue
                try:
                    mesh = _build_node_mesh(n, conns)
                    path = "%s/SM_SewerNode_%s" % (GENERATED_FOLDER, _safe(n.get_actor_label()))
                    crossing = _is_crossing(_node_type(n))
                    sm = _bake(mesh, path, list(_SLOTS), simple=False)
                    comp = n.get_component_by_class(unreal.StaticMeshComponent)
                    comp.modify()
                    comp.set_static_mesh(sm)
                    try:
                        comp.set_editor_property("override_materials", [])
                    except Exception:
                        pass
                except Exception as e:  # keep going, report at the end
                    warnings.append("%s: FAILED - %s" % (n.get_actor_label(), e))
            task.enter_progress_frame(1, "Placing passages")
            segs = _rebuild_network(edges, nodes, per_node)
    if SIMPLE_COLLISION:
        # box collision for crossings and rooms (set after everything is baked: set during the
        # bake it was lost again)
        import sewer_boxcol
        sewer_boxcol.apply_level_later(only=[n.get_path_name() for n in to_bake])

    msg = "Nodes baked: %d\nConnections: %d\nPassage segments: %d" % (len(to_bake), len(edges), segs)
    try:
        report = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_report.txt")
        open(report, "w").write(msg + "\n\nWarnings (%d):\n" % len(warnings) + "\n".join(warnings))
    except Exception:
        report = None
    if warnings:
        shown = warnings[:25]
        msg += "\n\nWarnings:\n- " + "\n- ".join(shown)
        if len(warnings) > len(shown):
            msg += "\n... and %d more (all in %s)" % (len(warnings) - len(shown), report)
        for w in warnings:
            unreal.log_warning("Sewer: " + w)
    unreal.log(msg)
    unreal.EditorDialog.show_message("Sewer Builder", msg, unreal.AppMsgType.OK)


def preview_profiles():
    """Spawns each passage mesh with its void prism on top, to check the profiles line up."""
    unreal.EditorAssetLibrary.make_directory(GENERATED_FOLDER)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    y = 0.0
    for ptype, pcfg in PASSAGE_TYPES.items():
        m = _new_mesh()
        _append_prism(m, _oriented(pcfg["void_profile"]), V(0, 0, 0), V(1, 0, 0), pcfg["segment_length"])
        void_sm = _bake(m, "%s/SM_DEBUG_Void_%s" % (GENERATED_FOLDER, ptype), None)
        passage_sm = unreal.EditorAssetLibrary.load_asset(pcfg["mesh"])
        rot = unreal.Rotator(0, 0, 0) if PASSAGE_MESH_POINTS_PLUS_X else unreal.Rotator(0, 0, 180)
        loc = V(0, y, 0) if PASSAGE_MESH_POINTS_PLUS_X else V(pcfg["segment_length"], y, 0)
        for sm, label, l, r in ((passage_sm, "DEBUG_Passage_" + ptype, loc, rot),
                                (void_sm, "DEBUG_Void_" + ptype, V(0, y, 0), unreal.Rotator(0, 0, 0))):
            a = eas.spawn_actor_from_class(unreal.StaticMeshActor, l, r)
            a.set_actor_label(label)
            a.static_mesh_component.set_static_mesh(sm)
        y += 1500.0
    unreal.log("Sewer: preview spawned. The DEBUG_Void should exactly fill each passage interior.")


def debug_voids(node_label):
    """Bake and spawn the void cutters of one node, to inspect them."""
    nodes = [a for a in _actors() if _is_node(a)]
    _, per_node = _gather(nodes, [])
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    node = [n for n in nodes if n.get_actor_label() == node_label][0]
    xf = node.get_actor_transform()
    rin = NODE_TYPES[_node_type(node)]["inner_radius"]
    i = 0
    for c in per_node[node.get_path_name()]:
        cc = dict(c)
        cc["h"] = unreal.MathLibrary.inverse_transform_direction(xf, c["h"]).normal()
        cc["d"] = unreal.MathLibrary.inverse_transform_direction(xf, c["d"]).normal()
        for v in _connection_voids(cc, rin):
            sm = _bake(v, "%s/SM_DEBUG_NodeVoid_%d" % (GENERATED_FOLDER, i), None)
            a = eas.spawn_actor_from_class(unreal.StaticMeshActor, node.get_actor_location(), node.get_actor_rotation())
            a.set_actor_label("DEBUG_NodeVoid_%d_%s_pitch%.1f" % (i, c["ptype"], c["pitch"]))
            a.static_mesh_component.set_static_mesh(sm)
            i += 1
