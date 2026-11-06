import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
DNP = '/Game/NightSky/BP_DayNightCycle'
DN = DNP + '.BP_DayNightCycle'
EG = DN + ':EventGraph'
# what does GetTime do with the timeline?
for x in infos(nodes(EG)):
    if 'DayNightCycleTimeline' in x['type_id'] or x['type_id'].endswith('|DayNightCycleTimeline'):
        out.append("timeline node %s inputs: %s" % (x['node']['refPath'].split('.')[-1], [(p['name'], [c['node']['refPath'].split('.')[-1] for c in (p.get('connected_pins') or [])]) for p in x['input_pins']]))
# 1. replicate the actor
cdo = DNP + '.Default__BP_DayNightCycle_C'
setprops(cdo, {'bReplicates': True, 'bAlwaysRelevant': True})
# 2. NetTime (X=hour, Y=day of year, Z=year), RepNotify
try: call('add_variable', {'blueprint': {'refPath': DN}, 'name': 'NetTime', 'type_name': 'Vector'})
except Exception as e: out.append("var: %s" % str(e)[:100])
call('set_variable_replication', {'blueprint': {'refPath': DN}, 'variable_name': 'NetTime', 'replication': 'RepNotify'})
compile_bp(DN)
gl = [g['refPath'] for g in call('list_graphs', {'blueprint': {'refPath': DN}})]
out.append("graphs now: %s" % [g.split(':')[-1] for g in gl])
msg = ['Class|BPISetTime|GetTime']
out.append("GetTime message candidates: %s" % msg)
# 3. OnRep_NetTime -> GetTime(hour, day, year) on self
orp = [g for g in gl if g.endswith(':OnRep_NetTime')][0]
for n_ in nodes(orp):
    if 'FunctionEntry' not in n_: call('delete_node', {'node': {'refPath': n_}})
if True:
    call('write_graph_dsl', {'graph': {'refPath': orp}, 'code': '''(fn OnRep_NetTime ()
  (bind t (Variables|Default|GetNetTime))
  (%s :Hour (.x t) :Day (Math|Float|Truncate (.y t)) :Year (Math|Float|Truncate (.z t))))''' % msg[0]})
out.append("OnRep_NetTime:\n" + str(call('read_graph_dsl', {'graph': {'refPath': orp}})))
# 4. SetNetTime(Hour, Day, Year) - call on the server
g = call('add_function_graph', {'blueprint': {'refPath': DN}, 'graph_name': 'SetNetTime'})['refPath']
if len(nodes(g)) <= 1:
    for n_, t_ in (('Hour', 'float'), ('Day', 'int'), ('Year', 'int')):
        call('add_function_param', {'graph': {'refPath': g}, 'param_name': n_, 'param_type': t_, 'input_param': True})
    call('write_graph_dsl', {'graph': {'refPath': g}, 'code': '''(fn SetNetTime (Hour Day Year)
  (Variables|Default|SetNetTime (Math|Vector|MakeVector Hour (Math|Conversions|ToFloat(Integer) Day) (Math|Conversions|ToFloat(Integer) Year))))'''})
out.append("SetNetTime:\n" + str(call('read_graph_dsl', {'graph': {'refPath': g}})))
# 5. ResyncTime: server pushes its current time (for late joiners)
g2 = call('add_function_graph', {'blueprint': {'refPath': DN}, 'graph_name': 'ResyncTime'})['refPath']
if len(nodes(g2)) <= 1:
    call('write_graph_dsl', {'graph': {'refPath': g2}, 'code': '''(fn ResyncTime ()
  (CallFunction|SetNetTime :Hour (Variables|Time|GetSolarTime) :Day (Variables|Date|GetDaysOfYear) :Year (Variables|Date|GetYear)))'''})
out.append("ResyncTime:\n" + str(call('read_graph_dsl', {'graph': {'refPath': g2}})))
try: compile_bp(DN); out.append("compile OK")
except Exception as e: out.append("compile FAIL " + str(e)[:700])
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class().get_name() == 'BP_DayNightCycle_C':
        a.modify(); a.set_replicates(True); a.set_editor_property('always_relevant', True)
        out.append("instance replicates=%s always_relevant=%s" % (a.get_editor_property('replicates'), a.get_editor_property('always_relevant')))
print("\n".join(out))
