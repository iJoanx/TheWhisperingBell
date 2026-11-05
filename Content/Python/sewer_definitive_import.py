"""Imports the definitive sewer kit (exported from Wall.blend with its UCX_ collision) into
/Game/Sewers/Meshes/Definitive and makes the builder use it from now on.

    py sewer_definitive_import.py

FBX files: Content/Python/import/definitive/<Piece>.fbx. Collision comes from the UCX_ parts
(no auto-generated collision). No materials or textures are imported: every slot gets
M_Master_Sewers_Inst.
The builder (sewer_builder.use_definitive) switches to these meshes whenever they exist."""
import os
import traceback
import unreal

PY_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(PY_DIR, "import", "definitive")
DEST = "/Game/Sewers/Meshes/Definitive"
MATERIAL = "/Game/Level/Sewers/M_Master_Sewers_Inst"   # every slot of every piece
PIECES = ["Passage12Defo", "Passage20Defo", "Passage12EndDefo", "Passage20EndDefo",
          "JunctionDefo", "ShaftDefo", "JunctionBaseDefo", "ShaftBaseDefo"]
EAL = unreal.EditorAssetLibrary
out = os.path.join(PY_DIR, "scan_out.txt")


def _log(msg):
    open(out, "a").write(msg + "\n")
    unreal.log("DEFINITIVE " + msg)


def _gs(name):
    import sewer_builder
    return sewer_builder.gs(name)


def _hulls(sm):
    try:
        return len(sm.get_editor_property("body_setup").get_editor_property("agg_geom").get_editor_property("convex_elems"))
    except Exception:
        return 0


def apply_collision(sm, col):
    """Simple collision = one convex hull per separate block of the piece's _COL mesh (this
    Unreal's FBX import ignores UCX_ parts, same as for the walls)."""
    m = unreal.DynamicMesh()
    _gs("copy_mesh_from_static_mesh")(col, m, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                      unreal.GeometryScriptMeshReadLOD())
    r = _gs("split_mesh_by_components")(m, unreal.DynamicMeshPool())
    parts = r[1] if isinstance(r, tuple) else r
    o = unreal.GeometryScriptCollisionFromMeshOptions()
    o.set_editor_property("method", unreal.GeometryScriptCollisionGenerationMethod.CONVEX_HULLS)
    o.set_editor_property("max_convex_hulls_per_mesh", 1)
    o.set_editor_property("simplify_hulls", False)
    o.set_editor_property("auto_detect_boxes", False)
    shapes = []
    for p in parts:
        c = _gs("generate_collision_from_mesh")(p, o)
        shapes.append(c[0] if isinstance(c, tuple) else c)
    total = _gs("combine_simple_collision_array")(shapes) if shapes else None
    total = total[0] if isinstance(total, tuple) else total
    if total is not None:
        _gs("set_simple_collision_of_static_mesh")(total, sm, unreal.GeometryScriptSetSimpleCollisionOptions())
    return _hulls(sm)


def _import(name, dest=DEST, materials=False):
    opts = unreal.FbxImportUI()
    opts.set_editor_property("import_mesh", True)
    opts.set_editor_property("import_materials", materials)
    opts.set_editor_property("import_textures", materials)
    opts.set_editor_property("import_as_skeletal", False)
    opts.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    sm = opts.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("combine_meshes", True)
    sm.set_editor_property("auto_generate_collision", False)     # the UCX_ parts are the collision
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(SRC, name + ".fbx"))
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", opts)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return EAL.load_asset(dest + "/" + name)


def run():
    open(out, "w").write("definitive import started\n")
    for name in PIECES:
        mesh = _import(name)
        if mesh is None:
            _log("%s: import FAILED" % name)
            continue
        mat = EAL.load_asset(MATERIAL)
        slots = mesh.get_editor_property("static_materials")
        for i in range(len(slots)):
            mesh.set_material(i, mat)
        reused = "%d slot(s) -> %s" % (len(slots), MATERIAL.split("/")[-1] if mat else "MISSING material")
        col = _import(name + "_COL", DEST + "/Collision", False)
        hulls = apply_collision(mesh, col) if col else 0
        bs = mesh.get_editor_property("body_setup")
        if bs:
            bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
        EAL.save_asset(DEST + "/" + name)
        b = mesh.get_bounding_box()
        cb = col.get_bounding_box() if col else None
        _log("%s: %d collision hulls, materials %s, bounds x %.0f..%.0f y %.0f..%.0f z %.0f..%.0f%s"
             % (name, hulls, reused, b.min.x, b.max.x, b.min.y, b.max.y, b.min.z, b.max.z,
                (" | collision x %.0f..%.0f y %.0f..%.0f z %.0f..%.0f" % (cb.min.x, cb.max.x, cb.min.y, cb.max.y,
                                                                         cb.min.z, cb.max.z)) if cb else ""))
    _log("done")


try:
    run()
except Exception:
    _log(traceback.format_exc())
