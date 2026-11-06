import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
DN = '/Game/NightSky/BP_DayNightCycle'
bp = unreal.load_asset(DN); bp.modify()
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); L = unreal.SubobjectDataBlueprintFunctionLibrary
for hd in sub.k2_gather_subobject_data_for_blueprint(bp):
    o = L.get_object(L.get_data(hd))
    if o is None: continue
    if isinstance(o, unreal.StaticMeshComponent):
        o.modify()
        before = (o.get_editor_property('cast_shadow'), o.get_editor_property('affect_distance_field_lighting'), o.get_editor_property('affect_dynamic_indirect_lighting'))
        o.set_editor_property('cast_shadow', False)
        o.set_editor_property('affect_distance_field_lighting', False)
        o.set_editor_property('affect_dynamic_indirect_lighting', False)
        print("%-14s %-30s shadow/DF/GI %s -> False" % (o.get_name(), o.static_mesh.get_name() if o.static_mesh else None, before))
    elif isinstance(o, unreal.LightComponentBase) or isinstance(o, unreal.ExponentialHeightFogComponent):
        print("info", o.get_name(), o.get_class().get_name())
compile_bp(DN + '.BP_DayNightCycle')
# level instance must not override these
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class().get_name() == 'BP_DayNightCycle_C':
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            print("instance", c.get_name(), c.get_editor_property('cast_shadow'), c.get_editor_property('affect_distance_field_lighting'), c.get_editor_property('affect_dynamic_indirect_lighting'))
