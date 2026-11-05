"""One-off setup helpers for the sewer system (run inside the UE editor).
    import importlib, sewer_setup; importlib.reload(sewer_setup)
    sewer_setup.import_passages()        # new Passage12/Passage20 into /Game/Sewers/Meshes/v2
    sewer_setup.make_water_material()    # T_SewerWater_N + M_SewerWater
    sewer_setup.import_end_piece()       # SM_SewerEnd12 (dead-end wall for Passage12)
    sewer_setup.import_end_piece("SewerEnd20.fbx", "SM_SewerEnd20")   # ... and for Passage20
"""
import os
import unreal

PY_DIR = os.path.dirname(os.path.abspath(__file__))
IMPORT_DIR = os.path.join(PY_DIR, "import")
MESH_DEST = "/Game/Sewers/Meshes/v2"
MAT_DEST = "/Game/Sewers/Materials"
TEX_DEST = "/Game/Sewers/Textures"

MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary


def _import(path, dest, name=None, options=None):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", dest)
    if name:
        task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    if options is not None:
        task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.get_editor_property("imported_object_paths") or [])


def import_passages(fbx="SewerPassages_v2.fbx"):
    paths = _import(os.path.join(IMPORT_DIR, fbx), MESH_DEST)
    for p in paths:
        unreal.log("SETUP imported " + p)
    return paths


def reimport_passage(fbx="Passage12.fbx", name="Passage12"):
    """Re-import one passage mesh from import/<fbx> over the existing asset, keeping the
    materials it had (by slot order) so nothing else changes."""
    path = MESH_DEST + "/" + name
    old = EAL.load_asset(path)
    keep = [s.get_editor_property("material_interface") for s in old.get_editor_property("static_materials")] \
        if old else []
    opts = unreal.FbxImportUI()
    opts.set_editor_property("import_mesh", True)
    opts.set_editor_property("import_materials", False)
    opts.set_editor_property("import_textures", False)
    opts.set_editor_property("import_as_skeletal", False)
    opts.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    sm = opts.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("combine_meshes", True)
    sm.set_editor_property("auto_generate_collision", False)
    _import(os.path.join(IMPORT_DIR, fbx), MESH_DEST, name, opts)
    mesh = EAL.load_asset(path)
    slots = mesh.get_editor_property("static_materials")
    for i in range(len(slots)):
        if i < len(keep) and keep[i]:
            mesh.set_material(i, keep[i])
    bs = mesh.get_editor_property("body_setup")
    if bs:
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    EAL.save_asset(path)
    unreal.log("SETUP re-imported %s (%d slots, kept %d materials)" % (path, len(slots), len(keep)))
    return mesh


def import_end_piece(fbx="SewerEnd12.fbx", name="SM_SewerEnd12"):
    """Your modelled dead-end wall. Pivot on the inner face, wall extends along +X."""
    opts = unreal.FbxImportUI()
    opts.set_editor_property("import_mesh", True)
    opts.set_editor_property("import_materials", False)     # reuse sewer1_00x already in v2
    opts.set_editor_property("import_textures", False)
    opts.set_editor_property("import_as_skeletal", False)
    opts.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    sm = opts.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("combine_meshes", True)
    sm.set_editor_property("auto_generate_collision", False)
    paths = _import(os.path.join(IMPORT_DIR, fbx), MESH_DEST, name, opts)
    mesh = EAL.load_asset(MESH_DEST + "/" + name)
    if mesh:
        _fix_end_winding(mesh)
        # FBX slots are named after the Blender materials: use what the passage meshes use for
        # the same slot name, else a material asset of that name (sewer1.002 -> sewer1_002)
        known = {}
        for p in ("Passage12", "Passage20"):
            pm = EAL.load_asset(MESH_DEST + "/" + p)
            for sl in (pm.get_editor_property("static_materials") if pm else []):
                if sl.get_editor_property("material_interface"):
                    known[str(sl.get_editor_property("material_slot_name")).lower()] = sl.get_editor_property("material_interface")
        for i, slot in enumerate(mesh.get_editor_property("static_materials")):
            nm = str(slot.get_editor_property("material_slot_name")).replace(".", "_")
            mat = known.get(nm.lower())
            if mat is None and EAL.does_asset_exist(MESH_DEST + "/" + nm):
                mat = EAL.load_asset(MESH_DEST + "/" + nm)
                if not isinstance(mat, unreal.MaterialInterface):
                    mat = None
            if mat:
                mesh.set_material(i, mat)
            else:
                unreal.log_warning("SETUP: no material asset for slot %s" % nm)
        bs = mesh.get_editor_property("body_setup")
        if bs:
            bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        EAL.save_asset(MESH_DEST + "/" + name)
    unreal.log("SETUP end piece: %s" % paths)
    return mesh


def _fix_end_winding(sm):
    """End pieces are slabs along X: every face lying on the slab's front or back plane must
    face outwards (-X at the front, +X at the back). Faces modelled the wrong way round are
    invisible from inside the passage, so flip them (keeping UVs and materials)."""
    import sewer_builder as sb
    gs = sb.gs
    m = unreal.DynamicMesh()
    gs("copy_mesh_from_static_mesh")(sm, m, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                     unreal.GeometryScriptMeshReadLOD())
    box = sm.get_bounding_box()
    lo, hi = box.min.x, box.max.x
    flips = []
    for t in range(gs("get_num_triangle_i_ds")(m)):
        vs = sb._tri_positions(m, t)
        if not vs:
            continue
        n = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        if n.length() < 1e-6:
            continue
        n = n.normal()
        cx = sum(v.x for v in vs) / 3.0
        # UE triangles are clockwise-front, so the geometric cross product points inwards
        if all(abs(v.x - lo) < 0.5 for v in vs) and n.x < -0.9:
            flips.append(t)
        elif all(abs(v.x - hi) < 0.5 for v in vs) and n.x > 0.9:
            flips.append(t)
    if not flips:
        return 0
    for t in flips:
        idx = gs("get_triangle_indices")(m, t)
        idx = idx[0] if isinstance(idx, tuple) else idx
        uv = gs("get_triangle_u_vs")(m, 0, t)
        uvs = [u for u in uv if isinstance(u, unreal.Vector2D)] if isinstance(uv, tuple) else []
        mid = gs("get_triangle_material_id")(m, t)
        mid = mid[0] if isinstance(mid, tuple) else mid
        gs("delete_triangle_from_mesh")(m, t)
        new = gs("add_triangle_to_mesh")(m, unreal.IntVector(idx.x, idx.z, idx.y))
        new = [x for x in new if isinstance(x, int)][0] if isinstance(new, tuple) else new
        gs("set_triangle_material_id")(m, int(new), int(mid))
        if len(uvs) == 3:
            tri = unreal.GeometryScriptUVTriangle()
            tri.set_editor_property("uv0", uvs[0])
            tri.set_editor_property("uv1", uvs[2])
            tri.set_editor_property("uv2", uvs[1])
            gs("set_mesh_triangle_u_vs")(m, 0, int(new), tri)
    sb._normals(m)
    gs("copy_mesh_to_static_mesh")(m, sm, unreal.GeometryScriptCopyMeshToAssetOptions(),
                                   unreal.GeometryScriptMeshWriteLOD())
    unreal.log("SETUP %s: flipped %d inward-facing triangles" % (sm.get_name(), len(flips)))
    return len(flips)


def _water_texture():
    tex_path = TEX_DEST + "/T_SewerWater_N"
    if not EAL.does_asset_exist(tex_path):
        _import(os.path.join(IMPORT_DIR, "T_SewerWater_N.png"), TEX_DEST, "T_SewerWater_N")
    tex = EAL.load_asset(tex_path)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    tex.set_editor_property("srgb", False)
    EAL.save_asset(tex_path)
    return tex


FLOW_HLSL = r"""
float2 dir = float2(DirX, DirY);
float len = length(dir);
dir = len > 0.001 ? dir / len : float2(1.0, 0.0);

// world-space UVs: identical pattern on every piece, so joints are seamless
float2 uv = WP.xy / TileSize;

// two-phase flow: each layer slides a bounded distance, then cross-fades into the other,
// so the pattern moves forever without ever stretching or snapping
// ease in/out along the strip (lead-in strips at crossings start/end still, so they
// meet the still crossing water without a seam). Fade: 0 none, 1 still at local x=0, 2 still at x=end
float f = saturate(LocalX / SegLen);
float ease = Fade < 0.5 ? 1.0 : (Fade < 1.5 ? smoothstep(0.0, 1.0, f) : smoothstep(0.0, 1.0, 1.0 - f));
Speed *= ease;

float t = Time * CycleRate;
float p0 = frac(t);
float p1 = frac(t + 0.5);
float travel = Speed * FlowStrength;
float w = abs(2.0 * p0 - 1.0);

float2 a0 = Texture2DSample(Tex, TexSampler, uv - dir * travel * p0).rg * 2.0 - 1.0;
float2 a1 = Texture2DSample(Tex, TexSampler, uv - dir * travel * p1 + 0.37).rg * 2.0 - 1.0;
float2 n = lerp(a0, a1, w);

// a larger, slower layer for variety (same flow direction)
float2 uv2 = WP.xy / (TileSize * 3.1) + 0.5;
float2 b0 = Texture2DSample(Tex, TexSampler, uv2 - dir * travel * 0.4 * p0).rg * 2.0 - 1.0;
float2 b1 = Texture2DSample(Tex, TexSampler, uv2 - dir * travel * 0.4 * p1 + 0.61).rg * 2.0 - 1.0;
n += lerp(b0, b1, w) * 0.6;

// faster water is rougher
n *= NormalStrength * (0.6 + 0.4 * saturate(Speed));
// WORLD-space normal, projected from the top: identical on every piece regardless of
// how the piece is oriented, so neighbouring pieces light exactly the same
return normalize(VN + float3(n, 0.0));
"""


def make_water_material():
    tex = _water_texture()
    path = MAT_DEST + "/M_SewerWater"
    if EAL.does_asset_exist(path):
        mat = EAL.load_asset(path)          # rebuild in place: keeps every reference to it
        MEL.delete_all_material_expressions(mat)
    else:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_SewerWater", MAT_DEST, unreal.Material, unreal.MaterialFactoryNew())
    # Opaque: overlapping water pieces never stack and need no dithering
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    for prop, val in (("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING),
                      ("used_with_instanced_static_meshes", True),
                      ("used_with_static_lighting", True)):
        try:
            mat.set_editor_property(prop, val)
        except Exception as e:  # noqa
            unreal.log_warning("SETUP: %s not set (%s)" % (prop, e))

    def node(cls, x, y):
        return MEL.create_material_expression(mat, cls, x, y)

    def scalar(name, value, x, y):
        n = node(unreal.MaterialExpressionScalarParameter, x, y)
        n.set_editor_property("parameter_name", name)
        n.set_editor_property("default_value", value)
        return n

    def custom_data(index, default, x, y):
        n = node(unreal.MaterialExpressionPerInstanceCustomData, x, y)
        n.set_editor_property("data_index", index)
        n.set_editor_property("const_default_value", default)
        return n

    # inputs
    wp = node(unreal.MaterialExpressionWorldPosition, -1400, -300)
    tm = node(unreal.MaterialExpressionTime, -1400, -200)
    tx = node(unreal.MaterialExpressionTextureObject, -1400, -100)
    tx.set_editor_property("texture", tex)
    dir_x = custom_data(0, 1.0, -1400, 0)
    dir_y = custom_data(1, 0.0, -1400, 100)
    speed = custom_data(2, 0.0, -1400, 200)     # non-instanced use = still water
    fade = custom_data(3, 0.0, -1600, 200)
    lp = node(unreal.MaterialExpressionLocalPosition, -1600, 0)
    lpx = node(unreal.MaterialExpressionComponentMask, -1500, 0)
    lpx.set_editor_property("r", True)
    lpx.set_editor_property("g", False)
    lpx.set_editor_property("b", False)
    lpx.set_editor_property("a", False)
    MEL.connect_material_expressions(lp, "", lpx, "")
    seg = scalar("SegLen", 400.0, -1600, 300)
    vn = node(unreal.MaterialExpressionVertexNormalWS, -1600, 400)
    tile = scalar("TileSize", 450.0, -1400, 300)
    cycle = scalar("CycleRate", 0.35, -1400, 400)
    flow = scalar("FlowStrength", 0.45, -1400, 500)
    nstr = scalar("NormalStrength", 0.35, -1400, 600)

    cu = node(unreal.MaterialExpressionCustom, -900, 100)
    cu.set_editor_property("code", FLOW_HLSL)
    cu.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    cu.set_editor_property("description", "SewerFlow")
    names = ["WP", "Time", "Tex", "DirX", "DirY", "Speed", "TileSize", "CycleRate", "FlowStrength", "NormalStrength",
             "LocalX", "Fade", "SegLen", "VN"]
    ins = []
    for nm in names:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", nm)
        ins.append(ci)
    cu.set_editor_property("inputs", ins)
    for src, nm in zip([wp, tm, tx, dir_x, dir_y, speed, tile, cycle, flow, nstr, lpx, fade, seg, vn], names):
        MEL.connect_material_expressions(src, "", cu, nm)
    MEL.connect_material_property(cu, "", unreal.MaterialProperty.MP_NORMAL)
    mat.set_editor_property("tangent_space_normal", False)

    # colour: murky, a little lighter where it runs fast (steep passages)
    deep = node(unreal.MaterialExpressionVectorParameter, -900, 400)
    deep.set_editor_property("parameter_name", "WaterColor")
    deep.set_editor_property("default_value", unreal.LinearColor(0.012, 0.018, 0.010, 1.0))
    foam = node(unreal.MaterialExpressionVectorParameter, -900, 550)
    foam.set_editor_property("parameter_name", "FastWaterColor")
    foam.set_editor_property("default_value", unreal.LinearColor(0.09, 0.1, 0.08, 1.0))
    sat = node(unreal.MaterialExpressionSubtract, -700, 650)          # speed - 1
    sat.set_editor_property("const_b", 1.0)
    # colour follows the same eased speed as the ripples, so a passage piece that eases in from a
    # crossing's still water is coloured exactly like it where they meet
    eased = node(unreal.MaterialExpressionCustom, -800, 650)
    eased.set_editor_property("code", "float f = saturate(LocalX / SegLen);\n"
                              "float e = Fade < 0.5 ? 1.0 : (Fade < 1.5 ? smoothstep(0.0, 1.0, f) : smoothstep(0.0, 1.0, 1.0 - f));\n"
                              "return Speed * e;")
    eased.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    eased.set_editor_property("description", "EasedSpeed")
    eins = []
    for nm in ("Speed", "Fade", "LocalX", "SegLen"):
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", nm)
        eins.append(ci)
    eased.set_editor_property("inputs", eins)
    for src, nm in zip([speed, fade, lpx, seg], ("Speed", "Fade", "LocalX", "SegLen")):
        MEL.connect_material_expressions(src, "", eased, nm)
    MEL.connect_material_expressions(eased, "", sat, "A")
    k = node(unreal.MaterialExpressionMultiply, -600, 650)
    k.set_editor_property("const_b", 0.35)
    MEL.connect_material_expressions(sat, "", k, "A")
    clamp = node(unreal.MaterialExpressionSaturate, -500, 650)
    MEL.connect_material_expressions(k, "", clamp, "")
    lerp = node(unreal.MaterialExpressionLinearInterpolate, -400, 450)
    MEL.connect_material_expressions(deep, "", lerp, "A")
    MEL.connect_material_expressions(foam, "", lerp, "B")
    MEL.connect_material_expressions(clamp, "", lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rough = scalar("Roughness", 0.12, -400, 750)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    spec = scalar("Specular", 0.35, -400, 850)
    MEL.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)

    MEL.recompile_material(mat)
    EAL.save_asset(path)
    unreal.log("SETUP water material built: " + path)
    return mat


def fix_grate_material(mi_name="sewer1_001", tex_name="sewer3", like="sewer1_002"):
    """The end piece's lower face uses sewer1.001, which in Blender shows the sewer3 grate
    texture; its imported material instance came through without it. Rebuild it like sewer1_002."""
    info = []
    ref = EAL.load_asset(MESH_DEST + "/" + like)
    mi = EAL.load_asset(MESH_DEST + "/" + mi_name)
    tex = EAL.load_asset(MESH_DEST + "/" + tex_name)
    info.append("ref parent=%s tex=%s" % (ref.get_editor_property("parent"),
                [(str(p.parameter_info.name), p.parameter_value) for p in ref.get_editor_property("texture_parameter_values")]))
    info.append("mi before parent=%s tex=%s" % (mi.get_editor_property("parent"),
                [(str(p.parameter_info.name), p.parameter_value) for p in mi.get_editor_property("texture_parameter_values")]))
    mi.set_editor_property("parent", ref.get_editor_property("parent"))
    names = [str(p.parameter_info.name) for p in ref.get_editor_property("texture_parameter_values")] or \
        [str(n) for n in MEL.get_texture_parameter_names(ref.get_editor_property("parent"))]
    for n in names:
        MEL.set_material_instance_texture_parameter_value(mi, n, tex)
    MEL.update_material_instance(mi)
    EAL.save_asset(MESH_DEST + "/" + mi_name)
    info.append("mi after tex=%s" % [(str(p.parameter_info.name), p.parameter_value)
                                      for p in mi.get_editor_property("texture_parameter_values")])
    open(os.path.join(PY_DIR, "scan_out.txt"), "w").write("\n".join(str(i) for i in info))
    unreal.log("SETUP grate material: " + " | ".join(info))


def match_end_uvs(end_name="SM_SewerEnd12", ptype="P12"):
    """Re-map the end piece's brick faces (front and back) so its brick rows line up with the
    passage's side walls: U runs across the wall at the passage's along-the-wall density, V is
    the side wall's V at the same height. Faces with other materials (the grate) are untouched."""
    import sewer_builder as sb
    gs = sb.gs
    sb._UV_TABLES.clear()
    table = sb._uv_table(ptype)
    passage = EAL.load_asset(sb.PASSAGE_TYPES[ptype]["mesh"])
    wall_mat = passage.get_editor_property("static_materials")[0].get_editor_property("material_interface")
    # the side wall: the vertical profile edge on the +Y side above the walkway
    wall = max((e for e in table if abs(e[0][0] - e[1][0]) < 0.5 and min(e[0][1], e[1][1]) >= -0.5),
               key=lambda e: e[0][0])
    (y0, z0), (y1, z1) = wall[0], wall[1]
    v_a, v_b = wall[3][0][1], wall[3][1][1]
    dv_dz = (v_b - v_a) / (z1 - z0)
    v_at = lambda z: v_a + (z - z0) * dv_dz  # noqa
    du_dy = abs(wall[4][0][0] - wall[3][0][0]) / 400.0   # same density as along the passage

    sm = EAL.load_asset(MESH_DEST + "/" + end_name)
    mats = [s.get_editor_property("material_interface") for s in sm.get_editor_property("static_materials")]
    m = unreal.DynamicMesh()
    gs("copy_mesh_from_static_mesh")(sm, m, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                     unreal.GeometryScriptMeshReadLOD())
    box = sm.get_bounding_box()
    n = 0
    for t in range(gs("get_num_triangle_i_ds")(m)):
        vs = sb._tri_positions(m, t)
        if not vs:
            continue
        mid = gs("get_triangle_material_id")(m, t)
        mid = mid[0] if isinstance(mid, tuple) else mid
        if mid >= len(mats) or mats[mid] != wall_mat:
            continue
        on_front = all(abs(v.x - box.min.x) < 0.5 for v in vs)
        on_back = all(abs(v.x - box.max.x) < 0.5 for v in vs)
        if not (on_front or on_back):
            continue
        sgn = 1.0 if on_front else -1.0
        tri = unreal.GeometryScriptUVTriangle()
        for k, name in enumerate(("uv0", "uv1", "uv2")):
            tri.set_editor_property(name, unreal.Vector2D(0.5 + sgn * vs[k].y * du_dy, v_at(vs[k].z)))
        gs("set_mesh_triangle_u_vs")(m, 0, t, tri, True)
        n += 1
    gs("copy_mesh_to_static_mesh")(m, sm, unreal.GeometryScriptCopyMeshToAssetOptions(),
                                   unreal.GeometryScriptMeshWriteLOD())
    EAL.save_asset(MESH_DEST + "/" + end_name)
    unreal.log("SETUP %s: re-mapped %d brick triangles to the %s wall layout" % (end_name, n, ptype))
    return n


# ----------------------------------------------------------------------------- flowing ripples
FLOW_UV_HLSL = r"""
// One continuous texture over the whole network, no cross-fade. The builder gives every point
// two smooth values: S = distance along the flow, T = the water's travel time to get there.
// The ripples run along T - Time, so they move at the water's own speed: fast water stretches
// them, slow water bunches them up. Balance mixes in plain distance (0 = true speeds and full
// stretch, 1 = same size everywhere but no speed difference). V = across the channel.
float S, T, P;
if (Mode > 0.5) {
    float f = saturate(LocalX / SegLen);
    float r = VB / max(VA, 0.01);
    float g = abs(r - 1.0) < 0.001 ? f : log(1.0 + (r - 1.0) * f) / log(r);
    S = lerp(SA, SB, f);
    T = lerp(TA, TB, g);
    P = LocalY;
} else {
    S = SA + Hub.x;
    T = TA + Hub.y;
    P = HubP.x;
}
float lam = saturate(Balance);
float k = (1.0 - lam) * VRef / TileSize;
float u = lam * S / TileSize + k * T - frac(k * Time);
float v = P / TileSize;
float a = Texture2DSample(Tex, TexSampler, float2(u, v)).a;
if (Mode < 0.5) {
    // crossings: each passage's flow carries in along its own arm; where the arms meet (the
    // middle and the corners between arms) it settles into still, world-aligned ripples
    float w = saturate((HubP.y - 0.35) / 0.5);
    w = w * w * (3.0 - 2.0 * w);
    // calm water: world-aligned, drifting slowly towards where this crossing's water goes
    float2 drift = frac(float2(VA, VB) * (Time * DriftSpeed / TileSize));   // per axis: wraps seamlessly
    // plus a slow, not-quite-circular wander: two sways with different periods, so the loop
    // never quite repeats the same way and comes back round to where it started now and then
    drift += SwirlR / TileSize * float2(sin(6.2831853 * Time / SwirlTX), sin(6.2831853 * Time / SwirlTY + 1.3));
    float still = Texture2DSample(Tex, TexSampler, WP.xy / TileSize - drift).a;
    a = lerp(still, a, w);
}
return a;
"""


FLOW_UV_HLSL_V2 = r"""
// v2: the same flow everywhere - passages AND crossings. Crossings carry smooth values of
// distance (S), travel time (T) and cross axis (P) that bend from each inflow to the outflows.
float lam = saturate(Balance);
float k = (1.0 - lam) * VRef / TileSize;
float S, T, P;
if (abs(Mode) > 0.5) {
    float f = saturate(LocalX / SegLen);
    float r = VB / max(VA, 0.01);
    float g = abs(r - 1.0) < 0.001 ? f : log(1.0 + (r - 1.0) * f) / log(r);
    S = lerp(SA, SB, f);
    T = lerp(TA, TB, g);
    P = LocalY * sign(Mode);
} else {
    S = SA + Hub.x;
    T = TA + Hub.y;
    P = HubP.x;
}
float u = lam * S / TileSize + k * T - frac(k * Time);
float a = Texture2DSample(Tex, TexSampler, float2(u, P / TileSize)).a;
if (abs(Mode) < 0.5) {
    // where the crossing's flow would be badly distorted (weight in UV3.y), calm water that
    // wanders in a slow, not-quite-circular loop takes over
    float w = saturate(HubP.y);
    w = w * w * (3.0 - 2.0 * w);
    float2 drift = SwirlR / TileSize * float2(sin(6.2831853 * Time / SwirlTX), sin(6.2831853 * Time / SwirlTY + 1.3));
    float still = Texture2DSample(Tex, TexSampler, WP.xy / TileSize - drift).a;
    a = lerp(still, a, w);
}
return a;
"""


FLOW_UV_HLSL_V3 = r"""
// v3: no flow at all. World-aligned ripples, same size everywhere, wandering slowly in a loose
// not-quite-circular loop (two sways with different periods) and back round now and then.
float2 drift = SwirlR / TileSize * float2(sin(6.2831853 * Time / SwirlTX), sin(6.2831853 * Time / SwirlTY + 1.3));
return Texture2DSample(Tex, TexSampler, WP.xy / TileSize - drift).a;
"""


def make_slw_material():
    """M_SewerWaterSLW + MI_SewerWaterSLW: the plain water layer UNDER the masked ripples (v5).
    Single Layer Water: one colour, sees the channel floor through it and gets murkier with
    depth (absorption / scattering); fully rough, no specular."""
    path = MAT_DEST + "/M_SewerWaterSLW"
    if EAL.does_asset_exist(path):
        mat = EAL.load_asset(path)
        MEL.delete_all_material_expressions(mat)
    else:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_SewerWaterSLW", MAT_DEST, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    try:
        mat.set_editor_property("used_with_instanced_static_meshes", True)
    except Exception:
        pass

    def vec(name, rgb, x, y):
        n = MEL.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, x, y)
        n.set_editor_property("parameter_name", name)
        n.set_editor_property("default_value", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
        return n

    def scalar(name, value, x, y):
        n = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
        n.set_editor_property("parameter_name", name)
        n.set_editor_property("default_value", value)
        return n
    MEL.connect_material_property(vec("WaterColor", (0.02, 0.035, 0.025), -500, -100), "",
                                  unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(scalar("Roughness", 1.0, -500, 50), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(scalar("Specular", 0.0, -500, 120), "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.connect_material_property(scalar("Metallic", 0.0, -500, 190), "", unreal.MaterialProperty.MP_METALLIC)
    out = MEL.create_material_expression(mat, unreal.MaterialExpressionSingleLayerWaterMaterialOutput, -150, 300)
    MEL.connect_material_expressions(vec("Scattering", (0.02, 0.04, 0.03), -500, 280), "", out, "ScatteringCoefficients")
    MEL.connect_material_expressions(vec("Absorption", (1.2, 0.7, 0.9), -500, 380), "", out, "AbsorptionCoefficients")
    MEL.connect_material_expressions(scalar("PhaseG", 0.0, -500, 480), "", out, "PhaseG")
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    mi_path = MAT_DEST + "/MI_SewerWaterSLW"
    if EAL.does_asset_exist(mi_path):
        mi = EAL.load_asset(mi_path)
    else:
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "MI_SewerWaterSLW", MAT_DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", mat)
    MEL.update_material_instance(mi)
    EAL.save_asset(mi_path)
    return mi_path


def _ripple_texture(png="T_SewerRipples.png"):
    name = os.path.splitext(png)[0]
    path = TEX_DEST + "/" + name
    _import(os.path.join(IMPORT_DIR, png), TEX_DEST, name)
    tex = EAL.load_asset(path)
    tex.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)      # crisp pixels, like the walls
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_PIXELS2D)
    EAL.save_asset(path)
    return tex


def make_flow_material(png="T_SewerRipples.png", v2=False, v3=False, v4=False, v5=False):
    """M_SewerWaterFlow (+ opaque / masked / translucent instances): your ripple texture moved by
    each piece's travel time (set by the builder per instance). Fully rough, no specular."""
    tex = _ripple_texture(png)
    mname = "M_SewerWaterFlowV5" if v5 else "M_SewerWaterFlowV4" if v4 else ("M_SewerWaterDriftV3" if v3 else ("M_SewerWaterFlowV2" if v2 else "M_SewerWaterFlow"))
    mi_prefix = "MI_SewerWaterV5_" if v5 else "MI_SewerWaterV4_" if v4 else ("MI_SewerWaterV3_" if v3 else ("MI_SewerWaterV2_" if v2 else "MI_SewerWater_"))
    path = MAT_DEST + "/" + mname
    if EAL.does_asset_exist(path):
        mat = EAL.load_asset(path)
        MEL.delete_all_material_expressions(mat)
    else:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            mname, MAT_DEST, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    for prop, val in (("used_with_instanced_static_meshes", True), ("used_with_static_lighting", True),
                      ("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)):
        try:
            mat.set_editor_property(prop, val)
        except Exception as e:  # noqa
            unreal.log_warning("SETUP: %s not set (%s)" % (prop, e))

    def node(cls, x, y):
        return MEL.create_material_expression(mat, cls, x, y)

    def scalar(name, value, x, y):
        n = node(unreal.MaterialExpressionScalarParameter, x, y)
        n.set_editor_property("parameter_name", name)
        n.set_editor_property("default_value", value)
        return n

    def custom_data(index, x, y):
        n = node(unreal.MaterialExpressionPerInstanceCustomData, x, y)
        n.set_editor_property("data_index", index)
        n.set_editor_property("const_default_value", 0.0)
        return n

    def mask(src, ch, x, y):
        m = node(unreal.MaterialExpressionComponentMask, x, y)
        for c in "rgba":
            m.set_editor_property(c, c == ch)
        MEL.connect_material_expressions(src, "", m, "")
        return m

    lp = node(unreal.MaterialExpressionLocalPosition, -1600, -200)
    tm = node(unreal.MaterialExpressionTime, -1600, -100)
    hub = node(unreal.MaterialExpressionTextureCoordinate, -1600, 560)
    hub.set_editor_property("coordinate_index", 2)
    hubp = node(unreal.MaterialExpressionTextureCoordinate, -1600, 640)
    hubp.set_editor_property("coordinate_index", 3)
    tx = node(unreal.MaterialExpressionTextureObjectParameter, -1600, -400)
    tx.set_editor_property("parameter_name", "Ripples")
    tx.set_editor_property("texture", tex)
    ins = [("Time", tm), ("Tex", tx), ("LocalX", mask(lp, "r", -1450, -220)), ("LocalY", mask(lp, "g", -1450, -160)),
           ("SA", custom_data(0, -1600, 0)), ("SB", custom_data(1, -1600, 80)),
           ("TA", custom_data(2, -1600, 160)), ("TB", custom_data(3, -1600, 240)),
           ("VA", custom_data(4, -1600, 320)), ("VB", custom_data(5, -1600, 400)),
           ("Mode", custom_data(6, -1600, 480)),
           ("Hub", hub), ("HubP", hubp), ("WP", node(unreal.MaterialExpressionWorldPosition, -1600, -300)),
           ("SegLen", scalar("SegLen", 400.0, -1600, 720)), ("TileSize", scalar("TileSize", 200.0, -1600, 800)),
           ("VRef", scalar("FlowRefSpeed", 60.0, -1600, 880)),
           ("Balance", scalar("StretchBalance", 0.3, -1600, 960)),
           ("DriftSpeed", scalar("CrossingDriftSpeed", 0.0, -1600, 1040)),
           ("SwirlR", scalar("CrossingSwirlRadius", 40.0, -1600, 1120)),
           ("SwirlTX", scalar("CrossingSwirlSecondsX", 23.0, -1600, 1200)),
           ("SwirlTY", scalar("CrossingSwirlSecondsY", 31.0, -1600, 1280))]
    cu = node(unreal.MaterialExpressionCustom, -1100, 100)
    cu.set_editor_property("code", FLOW_UV_HLSL_V3 if v3 else (FLOW_UV_HLSL_V2 if (v2 or v4 or v5) else FLOW_UV_HLSL))
    cu.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    cu.set_editor_property("description", "SewerFlowRipples")
    cins = []
    for nm, _ in ins:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", nm)
        cins.append(ci)
    cu.set_editor_property("inputs", cins)
    for nm, src in ins:
        MEL.connect_material_expressions(src, "", cu, nm)

    ripple = node(unreal.MaterialExpressionMultiply, -550, 200)       # texture alpha * strength
    MEL.connect_material_expressions(cu, "", ripple, "A")
    MEL.connect_material_expressions(scalar("RippleStrength", 1.0, -800, 350), "", ripple, "B")
    sat = node(unreal.MaterialExpressionSaturate, -420, 200)
    MEL.connect_material_expressions(ripple, "", sat, "")

    water = node(unreal.MaterialExpressionVectorParameter, -550, -100)
    water.set_editor_property("parameter_name", "WaterColor")
    water.set_editor_property("default_value", unreal.LinearColor(0.02, 0.035, 0.025, 1.0))
    rcol = node(unreal.MaterialExpressionVectorParameter, -550, 0)
    rcol.set_editor_property("parameter_name", "RippleColor")
    rcol.set_editor_property("default_value", unreal.LinearColor(0.32, 0.38, 0.33, 1.0))
    col = node(unreal.MaterialExpressionLinearInterpolate, -250, 0)
    MEL.connect_material_expressions(water, "", col, "A")
    MEL.connect_material_expressions(rcol, "", col, "B")
    MEL.connect_material_expressions(sat, "", col, "Alpha")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(scalar("Roughness", 1.0, -250, 250), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(scalar("Specular", 0.0, -250, 320), "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.connect_material_property(scalar("Metallic", 0.0, -250, 390), "", unreal.MaterialProperty.MP_METALLIC)
    # translucent: the water itself lets the channel show through, the ripples don't
    op = node(unreal.MaterialExpressionLinearInterpolate, -250, 470)
    MEL.connect_material_expressions(scalar("WaterOpacity", 0.6, -450, 470), "", op, "A")
    op.set_editor_property("const_b", 1.0)
    MEL.connect_material_expressions(sat, "", op, "Alpha")
    MEL.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    # masked: only the ripples are drawn
    MEL.connect_material_property(sat, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    MEL.recompile_material(mat)
    EAL.save_asset(path)

    made = []
    for suffix, blend in (("Opaque", unreal.BlendMode.BLEND_OPAQUE), ("Masked", unreal.BlendMode.BLEND_MASKED),
                          ("Translucent", unreal.BlendMode.BLEND_TRANSLUCENT)):
        mi_path = MAT_DEST + "/" + mi_prefix + suffix
        if EAL.does_asset_exist(mi_path):
            mi = EAL.load_asset(mi_path)
        else:
            f = unreal.MaterialInstanceConstantFactoryNew()
            mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                mi_prefix + suffix, MAT_DEST, unreal.MaterialInstanceConstant, f)
        mi.set_editor_property("parent", mat)
        ov = mi.get_editor_property("base_property_overrides")
        ov.set_editor_property("override_blend_mode", True)
        ov.set_editor_property("blend_mode", blend)
        mi.set_editor_property("base_property_overrides", ov)
        MEL.update_material_instance(mi)
        EAL.save_asset(mi_path)
        made.append(mi_path)
    unreal.log("SETUP flow water material: " + ", ".join(made))
    return made
