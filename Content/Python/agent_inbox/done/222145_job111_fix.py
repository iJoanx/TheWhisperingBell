import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
def T(g, f): return [x.get('type_id', x) if isinstance(x, dict) else x for x in types(g, f)]
out = []
M = '/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC'
g3 = M + ':ServerApplyTime'
cand = T(g3, 'BPDayNightCycle|')
out.append("DN class calls: %s" % [t for t in cand if 'Net' in t or 'Resync' in t])
sn = [t for t in cand if t.endswith('|SetNetTime')]
for n_ in nodes(g3):
    if 'FunctionEntry' not in n_: call('delete_node', {'node': {'refPath': n_}})
call('write_graph_dsl', {'graph': {'refPath': g3}, 'code': '''(fn ServerApplyTime (Hour Day Year)
  (bind dn (Actor|GetActorOfClass "/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle_C"))
  (if (Utilities|IsValid(pure) dn)
    (%s :self dn :Hour Hour :Day Day :Year Year)))''' % sn[0]})
out.append(str(call('read_graph_dsl', {'graph': {'refPath': g3}})))
compile_bp(M)
# widget: call the server event
W = '/Game/Menus/WB_SetTime.WB_SetTime'; WEG = W + ':EventGraph'
ev = [t for t in T(WEG, 'SetTimeSignature') + T(WEG, 'BPMasterPC|SetTime')]
out.append("widget sees: %s" % ev)
print("\n".join(out))
