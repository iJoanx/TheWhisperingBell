"""Sewer water seen from below.

The sewer water strips (components tagged Water_Sewage) are one-sided and face up, using the normal
opaque flow material. This adds, next to each one, a copy facing down that uses the Single Layer
Water material (UNDERSIDE_MATERIAL), so from under the surface you look up at real water.
The copy uses the same instances with a "turned over" version of the mesh (same shape, faces
pointing down; made once per mesh in MESH_FOLDER), so sloped crossing pieces line up exactly.

Re-run after regenerating the sewers:   py import sewer_water_underside; sewer_water_underside.run()
Re-fit existing copies:                  py import sewer_water_underside; sewer_water_underside.refit()
Remove the copies:                       py import sewer_water_underside; sewer_water_underside.remove()
"""
import unreal

SOURCE_TAG = "Water_Sewage"
UNDERSIDE_TAG = "Water_Underside"
SUFFIX = "_Underside"
UNDERSIDE_MATERIAL = "/Game/Water/MI_SewerWater_Underside"
SEWER_TAG = "RDL_Sewers"
MESH_FOLDER = "/Game/Sewers/Generated/Underside"
_FLIPPED = {}


def flipped_mesh(mesh):
    """The same mesh with every face turned to point the other way (cached per mesh, saved as an asset)."""
    key = mesh.get_path_name()
    if key in _FLIPPED and _FLIPPED[key]:
        return _FLIPPED[key]
    path = "%s/%s_Underside" % (MESH_FOLDER, mesh.get_name())
    eal = unreal.EditorAssetLibrary
    if eal.does_asset_exist(path):
        asset = eal.load_asset(path)
    else:
        dyn = unreal.DynamicMesh()
        read = unreal.GeometryScriptMeshReadLOD()
        read.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
        dyn, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(
            mesh, dyn, unreal.GeometryScriptCopyMeshFromAssetOptions(), read)
        unreal.GeometryScript_Normals.flip_normals(dyn)
        # copy the original asset (keeps its settings), then write the turned-over geometry into it
        asset = eal.duplicate_asset(mesh.get_path_name(), path)
        if asset is None:
            raise RuntimeError("Could not create %s" % path)
        unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
            dyn, asset, unreal.GeometryScriptCopyMeshToAssetOptions(), unreal.GeometryScriptMeshWriteLOD())
    _FLIPPED[key] = asset
    return asset


def _sewer_actors():
    world = unreal.EditorLevelLibrary.get_editor_world()
    return unreal.GameplayStatics.get_all_actors_with_tag(world, SEWER_TAG)


def _add_hism(actor, name, mesh):
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
    comp.set_static_mesh(mesh)
    return comp


def _flip(top_z):
    """Mirror the mesh through its own top face: same outline, now facing down."""
    return unreal.Transform(location=unreal.Vector(0.0, 0.0, 2.0 * top_z),
                            rotation=unreal.Rotator(0.0, 0.0, 0.0),
                            scale=unreal.Vector(1.0, 1.0, -1.0))


def run():
    material = unreal.EditorAssetLibrary.load_asset(UNDERSIDE_MATERIAL)
    if material is None:
        raise RuntimeError("Missing %s" % UNDERSIDE_MATERIAL)
    made = skipped = instances = 0
    for actor in _sewer_actors():
        comps = actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
        existing = {c.get_name() for c in comps}
        for src in comps:
            if unreal.Name(SOURCE_TAG) not in list(src.component_tags):
                continue
            name = src.get_name() + SUFFIX
            if name in existing:
                skipped += 1
                continue
            mesh = src.get_editor_property("static_mesh")
            if mesh is None:
                continue
            actor.modify()
            dst = _add_hism(actor, name, flipped_mesh(mesh))
            dst.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            dst.set_material(0, material)
            dst.set_editor_property("cast_shadow", False)
            dst.component_tags = [unreal.Name(UNDERSIDE_TAG)]
            floats = src.get_editor_property("num_custom_data_floats")
            dst.set_editor_property("num_custom_data_floats", floats)
            data = list(src.get_editor_property("per_instance_sm_custom_data")) if floats else []
            for i in range(src.get_instance_count()):
                idx = dst.add_instance(src.get_instance_transform(i, False), False)
                for k in range(floats):
                    dst.set_custom_data_value(idx, k, data[i * floats + k], False)
                instances += 1
            try:
                dst.mark_render_state_dirty()
            except AttributeError:
                pass  # not exposed to Python here; the instances still show
            made += 1
    unreal.log("Sewer underside: %d components (%d instances) added, %d already there" % (made, instances, skipped))
    return made, instances, skipped


def refit():
    """Existing copies: switch to the turned-over mesh and put every instance exactly on its source."""
    fixed = instances = 0
    for actor in _sewer_actors():
        comps = {c.get_name(): c for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent)}
        for name, dst in comps.items():
            if unreal.Name(UNDERSIDE_TAG) not in list(dst.component_tags):
                continue
            src = comps.get(name[:-len(SUFFIX)]) if name.endswith(SUFFIX) else None
            if src is None:
                continue
            actor.modify()
            dst.modify()
            dst.set_static_mesh(flipped_mesh(src.get_editor_property("static_mesh")))
            n = min(src.get_instance_count(), dst.get_instance_count())
            for i in range(n):
                dst.update_instance_transform(i, src.get_instance_transform(i, False), False, True, True)
                instances += 1
            fixed += 1
    unreal.log("Sewer underside: refitted %d components (%d instances)" % (fixed, instances))
    return fixed, instances


def remove():
    removed = 0
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for actor in _sewer_actors():
        handles = sds.k2_gather_subobject_data_for_instance(actor)
        doomed = []
        for h in handles:
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
            if isinstance(obj, unreal.InstancedStaticMeshComponent) and unreal.Name(UNDERSIDE_TAG) in list(obj.component_tags):
                doomed.append(h)
        if doomed:
            actor.modify()
            sds.delete_subobjects(handles[0], doomed, None)
            removed += len(doomed)
    unreal.log("Sewer underside: removed %d components" % removed)
    return removed
