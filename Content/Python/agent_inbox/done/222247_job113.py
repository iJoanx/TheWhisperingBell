import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
def T(g, f): return [x.get('type_id', x) if isinstance(x, dict) else x for x in types(g, f)]
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
E = '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry'
for bp, vs in ((DN, ['NetTime0', 'NetTime1']), (E, ['bGoingDown0'])):
    for v in vs:
        try: call('remove_variable', {'blueprint': {'refPath': bp}, 'variable_name': v}); print("removed", v)
        except Exception as e: print("remove", v, str(e)[:200])
    print(bp.split('.')[-1], "vars:", [x for x in call('list_variables', {'blueprint': {'refPath': bp}}) if 'Net' in x or 'Going' in x])
    compile_bp(bp)
M = '/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC'
MEG = M + ':EventGraph'
print("in master:", [t for t in T(MEG, 'SetTimeSignature')])
W = '/Game/Menus/WB_SetTime.WB_SetTime:EventGraph'
for guess in ('Class|BPMasterPC|SetTimeSignatureEvent', 'Class|BPMasterPC|SetTimeSignature_Event'):
    try:
        n = node(W, guess, 0, 4000); print("widget created", guess, n); call('delete_node', {'node': {'refPath': n}})
    except Exception as e: print("guess", guess, str(e)[:120])
