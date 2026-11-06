import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
def T(g, f): return [x.get('type_id', x) if isinstance(x, dict) else x for x in types(g, f)]
WEG = '/Game/Menus/WB_SetTime.WB_SetTime:EventGraph'
for f in ('SetTimeSignature', 'ServerApplyTime', 'BPMasterPC|'):
    print(f, T(WEG, f)[:40])
M = '/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC'
print("events:", [e for e in (call('list_events', {'blueprint': {'refPath': M}}) or []) if 'Time' in str(e)][:10])
print("widget dangling:", [(x['node']['refPath'].split('.')[-1], x['type_id']) for x in infos(nodes(WEG)) if x['type_id'] in ('Player|GetOwningPlayerPawn',) or 'CastToBP_Master_PC' in x['type_id']])
print(str(call('read_graph_dsl', {'graph': {'refPath': M + ':ServerApplyTime'}})))
