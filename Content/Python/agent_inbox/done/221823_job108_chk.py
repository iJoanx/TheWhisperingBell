import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
for g in ('OnRep_NetTime', 'SetNetTime', 'ResyncTime'):
    print(str(call('read_graph_dsl', {'graph': {'refPath': DN + ':' + g}})))
try: compile_bp(DN); print("compile OK")
except Exception as e: print("compile FAIL", str(e)[:600])
print("CDO", getprops('/Game/NightSky/BP_DayNightCycle.Default__BP_DayNightCycle_C', ['bReplicates', 'bAlwaysRelevant']))
print("NetTime rep:", call('get_variable_replication', {'blueprint': {'refPath': DN}, 'variable_name': 'NetTime'}))
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class().get_name() == 'BP_DayNightCycle_C':
        print("instance replicates", a.get_editor_property('replicates'), "always_relevant", a.get_editor_property('always_relevant'))
