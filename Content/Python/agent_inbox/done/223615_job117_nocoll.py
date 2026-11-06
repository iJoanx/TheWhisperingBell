import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
DN = '/Game/NightSky/BP_DayNightCycle'
bp = unreal.load_asset(DN); bp.modify()
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); L = unreal.SubobjectDataBlueprintFunctionLibrary
for hd in sub.k2_gather_subobject_data_for_blueprint(bp):
    o = L.get_object(L.get_data(hd))
    if isinstance(o, unreal.StaticMeshComponent):
        o.modify()
        before = (str(o.get_collision_profile_name()), o.get_editor_property('generate_overlap_events'))
        o.set_collision_profile_name('NoCollision')
        o.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        o.set_editor_property('generate_overlap_events', False)
        print("%-28s collision/overlaps %s -> NoCollision/False" % (o.get_name(), before))
compile_bp(DN + '.BP_DayNightCycle')
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class().get_name() == 'BP_DayNightCycle_C':
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            print("instance", c.get_name(), c.get_collision_profile_name(), c.get_editor_property('generate_overlap_events'), c.get_collision_enabled())
