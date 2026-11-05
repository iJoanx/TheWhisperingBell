"""Wall kit setup (Zippy): imports the pieces exported from Wall.blend and gives them ONE material
that samples a Texture2DArray (layer per face in UV channel 1).
    py import importlib, walls_setup; importlib.reload(walls_setup); walls_setup.setup()
"""
import json
import os
import unreal

PY_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(PY_DIR, "import", "walls")
ROOT = "/Game/Walls"
MESHES = ROOT + "/Meshes"
COLLISION = ROOT + "/Collision"     # plain-mesh copies of the UCX collision, used by the wall spline
ARRAY = ROOT + "/T_Walls_Array"
MATERIAL = ROOT + "/M_Walls"
# texture file -> array layer (order of the array's source textures)
LAYERS = [("037", ROOT + "/NDS_Texture_037"), ("040", ROOT + "/NDS_Texture_040")]
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary


def _gs():
    import sewer_builder
    return sewer_builder


# --------------------------------------------------------------------------- texture array
def make_array():
    texs = []
    for _, p in LAYERS:
        t = EAL.load_asset(p)
        if not t:
            raise RuntimeError("missing texture " + p)
        t.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
        t.set_editor_property("srgb", True)
        EAL.save_asset(p)
        texs.append(t)
    arr = EAL.load_asset(ARRAY)
    if not arr:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        arr = tools.create_asset(ARRAY.split("/")[-1], ROOT, unreal.Texture2DArray, unreal.Texture2DArrayFactory())
    arr.set_editor_property("source_textures", texs)
    for prop, val in (("filter", unreal.TextureFilter.TF_NEAREST), ("srgb", True)):
        try:
            arr.set_editor_property(prop, val)
        except Exception as e:  # noqa
            unreal.log_warning("Walls: %s not set on array (%s)" % (prop, e))
    for fn in ("update_source_from_source_textures", "update_resource"):
        try:
            getattr(arr, fn)()
        except Exception:
            pass
    EAL.save_asset(ARRAY)
    return arr


# --------------------------------------------------------------------------- material
def make_material(arr):
    if EAL.does_asset_exist(MATERIAL):
        mat = EAL.load_asset(MATERIAL)
        MEL.delete_all_material_expressions(mat)
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = tools.create_asset(MATERIAL.split("/")[-1], ROOT, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)   # Blender: colour straight to the surface
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("two_sided", True)                                        # Blender: no backface culling
    mat.set_editor_property("opacity_mask_clip_value", 0.5)

    def E(cls, x, y):
        return MEL.create_material_expression(mat, cls, x, y)
    uv0 = E(unreal.MaterialExpressionTextureCoordinate, -900, 0)
    uv1 = E(unreal.MaterialExpressionTextureCoordinate, -900, 150)
    uv1.set_editor_property("coordinate_index", 1)
    layer = E(unreal.MaterialExpressionComponentMask, -700, 150)
    layer.set_editor_property("r", True)
    layer.set_editor_property("g", False)
    MEL.connect_material_expressions(uv1, "", layer, "")
    app = E(unreal.MaterialExpressionAppendVector, -500, 50)
    MEL.connect_material_expressions(uv0, "", app, "A")
    MEL.connect_material_expressions(layer, "", app, "B")
    tex = E(unreal.MaterialExpressionTextureSampleParameter2DArray, -300, 0) \
        if hasattr(unreal, "MaterialExpressionTextureSampleParameter2DArray") else E(unreal.MaterialExpressionTextureSample, -300, 0)
    try:
        tex.set_editor_property("parameter_name", "Atlas")
    except Exception:
        pass
    tex.set_editor_property("texture", arr)
    tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    MEL.connect_material_expressions(app, "", tex, "UVs")
    # Blender multiplies the (linear) colour attribute with the texture; UE hands the vertex
    # colour over as stored (sRGB bytes), so bring it to linear first
    vc = E(unreal.MaterialExpressionVertexColor, -500, 300)
    gamma = E(unreal.MaterialExpressionScalarParameter, -500, 420)
    gamma.set_editor_property("parameter_name", "VertexColorGamma")
    gamma.set_editor_property("default_value", 2.2)
    pw = E(unreal.MaterialExpressionPower, -300, 300)
    MEL.connect_material_expressions(vc, "", pw, "Base")
    MEL.connect_material_expressions(gamma, "", pw, "Exponent")
    mul = E(unreal.MaterialExpressionMultiply, -50, 100)
    MEL.connect_material_expressions(tex, "RGB", mul, "A")
    MEL.connect_material_expressions(pw, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)   # used if switched to Lit
    # only layer 0 (037) is cut out by its alpha in Blender; other layers are opaque
    mx = E(unreal.MaterialExpressionMax, -50, 300)
    MEL.connect_material_expressions(tex, "A", mx, "A")
    MEL.connect_material_expressions(layer, "", mx, "B")
    MEL.connect_material_property(mx, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    MEL.recompile_material(mat)
    EAL.save_asset(MATERIAL)
    return mat


# --------------------------------------------------------------------------- meshes
def _import(fbx, name, dest=MESHES):
    opts = unreal.FbxImportUI()
    opts.set_editor_property("import_mesh", True)
    opts.set_editor_property("import_materials", False)
    opts.set_editor_property("import_textures", False)
    opts.set_editor_property("import_as_skeletal", False)
    opts.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    sm = opts.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("combine_meshes", True)
    sm.set_editor_property("auto_generate_collision", False)
    try:
        sm.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
    except Exception:
        pass
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", fbx)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", opts)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return EAL.load_asset(dest + "/" + name)


def _norm(s):
    return str(s).replace(".", "_").replace(" ", "_").lower()


def convert_mesh(sm, piece, mat):
    """Material slots -> array layer in UV1, then a single material slot."""
    sb = _gs()
    gs = sb.gs
    layer_of_slot = {}
    for i, slot in enumerate(sm.get_editor_property("static_materials")):
        nm = _norm(slot.get_editor_property("material_slot_name"))
        layer = None
        for m, t in zip(piece["mats"], piece["textures"]):
            if m and _norm(m) == nm and t:
                layer = next((k for k, (key, _) in enumerate(LAYERS) if key in t), None)
        layer_of_slot[i] = 0 if layer is None else layer
        if layer is None:
            unreal.log_warning("Walls: %s slot %s has no known texture, using layer 0" % (sm.get_name(), nm))
    m = unreal.DynamicMesh()
    gs("copy_mesh_from_static_mesh")(sm, m, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    sb._ensure_uv_sets(m, 2)
    gs("enable_material_i_ds")(m)
    for t in range(gs("get_num_triangle_i_ds")(m)):
        try:
            mid = gs("get_triangle_material_id")(m, t)
            mid = mid[0] if isinstance(mid, tuple) else mid
        except Exception:
            mid = 0
        lay = float(layer_of_slot.get(int(mid), 0))
        sb._set_uv_triangle(m, 1, t, [(lay, 0.0)] * 3)
        gs("set_triangle_material_id")(m, t, 0, True)
    opts = unreal.GeometryScriptCopyMeshToAssetOptions()
    opts.set_editor_property("replace_materials", True)
    opts.set_editor_property("new_materials", [mat])
    try:
        opts.set_editor_property("new_material_slot_names", ["Walls"])
    except Exception:
        pass
    opts.set_editor_property("enable_recompute_normals", False)
    opts.set_editor_property("enable_recompute_tangents", False)
    gs("copy_mesh_to_static_mesh")(m, sm, opts, unreal.GeometryScriptMeshWriteLOD())
    sm.set_material(0, mat)
    bs = sm.get_editor_property("body_setup")
    if bs:
        # collision = the UCX parts from Blender (solid body + thick parapets), for everything,
        # incl. traces; the render mesh's see-through parapets play no part
        n = _convex_count(sm)
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT if n
                               else unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    try:
        sb._set_nanite(sm)
    except Exception:
        pass
    keep_uv1(sm)
    return layer_of_slot


def apply_collision(sm, col):
    """The piece's simple collision = exactly one convex hull per separate part of its _COL mesh
    (solid body, parapet slabs); complex collision = the render mesh (project default)."""
    gs = _gs().gs
    m = unreal.DynamicMesh()
    gs("copy_mesh_from_static_mesh")(col, m, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    r = gs("split_mesh_by_components")(m, unreal.DynamicMeshPool())
    parts = r[1] if isinstance(r, tuple) else r                # (mesh, component meshes)
    o = unreal.GeometryScriptCollisionFromMeshOptions()
    o.set_editor_property("method", unreal.GeometryScriptCollisionGenerationMethod.CONVEX_HULLS)
    o.set_editor_property("max_convex_hulls_per_mesh", 1)
    o.set_editor_property("simplify_hulls", False)
    o.set_editor_property("auto_detect_boxes", False)
    shapes = []
    for p in parts:
        c = gs("generate_collision_from_mesh")(p, o)
        shapes.append(c[0] if isinstance(c, tuple) else c)
    total = gs("combine_simple_collision_array")(shapes) if shapes else None
    total = total[0] if isinstance(total, tuple) else total
    if total is not None:
        gs("set_simple_collision_of_static_mesh")(total, sm, unreal.GeometryScriptSetSimpleCollisionOptions())
    bs = sm.get_editor_property("body_setup")
    if bs:
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)   # simple and complex
    EAL.save_asset(sm.get_path_name().split(".")[0])
    return _convex_count(sm)


def _convex_count(sm):
    try:
        return len(sm.get_editor_property("body_setup").get_editor_property("agg_geom").get_editor_property("convex_elems"))
    except Exception:
        return 0


def keep_uv1(sm):
    """UV channel 1 holds the texture-array layer: stop Unreal generating lightmap UVs into it
    (that is what scrambled the textures on the tower meshes)."""
    ses = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for lod in range(max(1, sm.get_num_lods())):
        bs = ses.get_lod_build_settings(sm, lod)
        bs.set_editor_property("generate_lightmap_u_vs", False)
        ses.set_lod_build_settings(sm, lod, bs)
    sm.set_editor_property("light_map_coordinate_index", 0)
    EAL.save_asset(sm.get_path_name().split(".")[0])


def fix_uvs():
    """Applies keep_uv1 to every mesh in Content/Walls/Meshes."""
    out = []
    for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(MESHES):
        sm = a.get_asset()
        if isinstance(sm, unreal.StaticMesh):
            keep_uv1(sm)
            out.append(sm.get_name())
    return out


def setup():
    pieces = json.load(open(os.path.join(SRC, "pieces.json")))
    arr = make_array()
    mat = make_material(arr)
    report = []
    for name, piece in pieces.items():
        fbx = os.path.join(SRC, name + ".fbx")
        import walls_spline
        sm = _import(fbx, walls_spline.RENAMES.get("SM_" + name, "SM_" + name))
        if not sm:
            report.append("%s: import failed" % name)
            continue
        lay = convert_mesh(sm, piece, mat)
        b = sm.get_bounding_box()
        report.append("%s: layers %s bounds %s %s, collision parts %d" % (
            name, lay, (round(b.min.x), round(b.min.y), round(b.min.z)), (round(b.max.x), round(b.max.y), round(b.max.z)),
            _convex_count(sm)))
        col_fbx = os.path.join(SRC, name + "_COL.fbx")
        if os.path.exists(col_fbx):
            col = _import(col_fbx, sm.get_name() + "_COL", COLLISION)
            if col:
                keep_uv1(col)
                report.append("   collision: %d convex parts" % apply_collision(sm, col))
    open(os.path.join(PY_DIR, "scan_out.txt"), "w").write("\n".join(report))
    unreal.log("Walls setup:\n" + "\n".join(report))
    return report


def show(z=0.0):
    """Places every piece in a row in the open level (labels Walls_Preview_*) to compare with Blender."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.get_actor_label().startswith("Walls_Preview_"):
            eas.destroy_actor(a)
    x = 0.0
    for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(MESHES):
        sm = a.get_asset()
        b = sm.get_bounding_box()
        w = b.max.x - b.min.x
        x += w * 0.5 + 300
        act = eas.spawn_actor_from_object(sm, unreal.Vector(x, 0, z))
        act.set_actor_label("Walls_Preview_" + sm.get_name())
        x += w * 0.5


def apply_all_collision():
    """Re-applies collision to every piece that has a _COL mesh; writes a report to scan_out.txt."""
    out = []
    for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(MESHES):
        n = str(a.asset_name)
        if EAL.does_asset_exist(COLLISION + "/" + n + "_COL"):
            out.append("%s: %d convex parts" % (n, apply_collision(EAL.load_asset(MESHES + "/" + n),
                                                                  EAL.load_asset(COLLISION + "/" + n + "_COL"))))
    open(os.path.join(PY_DIR, "scan_out.txt"), "w").write("\n".join(out))
    return out


def apply_collision_one(name):
    """Collision for one mesh (by asset name), logged to collision_log.txt before and after."""
    log = os.path.join(PY_DIR, "collision_log.txt")
    with open(log, "a") as f:
        f.write("start %s\n" % name)
    n = apply_collision(EAL.load_asset(MESHES + "/" + name), EAL.load_asset(COLLISION + "/" + name + "_COL"))
    with open(log, "a") as f:
        f.write("done %s: %d convex parts\n" % (name, n))
    return n


def reimport_collision():
    """Re-imports only the _COL meshes and re-applies collision, one piece at a time (logged)."""
    import walls_spline
    pieces = json.load(open(os.path.join(SRC, "pieces.json")))
    out = []
    for name in pieces:
        asset = walls_spline.RENAMES.get("SM_" + name, "SM_" + name)
        col_fbx = os.path.join(SRC, name + "_COL.fbx")
        if os.path.exists(col_fbx):
            _import(col_fbx, asset + "_COL", COLLISION)
            out.append("%s: %d" % (asset, apply_collision_one(asset)))
    return out


def reimport_piece(name):
    """Re-imports one piece (Blender name, e.g. 'wall') with its collision; saves everything."""
    import walls_spline
    pieces = json.load(open(os.path.join(SRC, "pieces.json")))
    mat = EAL.load_asset(MATERIAL)
    asset = walls_spline.RENAMES.get("SM_" + name, "SM_" + name)
    sm = _import(os.path.join(SRC, name + ".fbx"), asset)
    convert_mesh(sm, pieces[name], mat)
    col_fbx = os.path.join(SRC, name + "_COL.fbx")
    if os.path.exists(col_fbx):
        _import(col_fbx, asset + "_COL", COLLISION)
        apply_collision_one(asset)
    walls_spline._SRC.clear()
    walls_spline.rebuild_all()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return asset


def reimport_all(skip=()):
    """Re-imports every piece exported from Blender (pieces.json) with its collision, rebuilds the
    walls and saves. Report in scan_out.txt."""
    import walls_spline
    pieces = json.load(open(os.path.join(SRC, "pieces.json")))
    mat = EAL.load_asset(MATERIAL)
    out = []
    for name in pieces:
        if name in skip:
            continue
        asset = walls_spline.RENAMES.get("SM_" + name, "SM_" + name)
        sm = _import(os.path.join(SRC, name + ".fbx"), asset)
        if not sm:
            out.append("%s: import failed" % name)
            continue
        convert_mesh(sm, pieces[name], mat)
        n = 0
        col_fbx = os.path.join(SRC, name + "_COL.fbx")
        if os.path.exists(col_fbx):
            col = _import(col_fbx, asset + "_COL", COLLISION)
            if col:
                keep_uv1(col)
                n = apply_collision(sm, col)
        b = sm.get_bounding_box()
        out.append("%s: %d convex parts, bounds %s %s, trace %s" % (
            asset, n, (round(b.min.x), round(b.min.y), round(b.min.z)), (round(b.max.x), round(b.max.y), round(b.max.z)),
            sm.get_editor_property("body_setup").get_editor_property("collision_trace_flag")))
        open(os.path.join(PY_DIR, "scan_out.txt"), "w").write("\n".join(out))
    walls_spline.make_blueprint()
    walls_spline._SRC.clear()
    walls_spline.rebuild_all()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    out.append("done")
    open(os.path.join(PY_DIR, "scan_out.txt"), "w").write("\n".join(out))
    return out
