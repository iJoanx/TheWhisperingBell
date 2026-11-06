import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as BT
print("add_node_pin:", (BT.add_node_pin.__doc__ or "")[:900])
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle:EventGraph'
for f in ('GetTime', 'SetTimer', 'HasAuthority', 'GetOwningPlayerPawn'):
    print(f, [x.get('type_id', x) if isinstance(x, dict) else x for x in types(DN, f)][:20])
W = '/Game/Menus/WB_SetTime.WB_SetTime:EventGraph'
print("widget GetTime nodes:", [(x['node']['refPath'].split('.')[-1], [p['name'] for p in x['input_pins']]) for x in infos(nodes(W)) if 'GetTime' in x['type_id']])
print("widget pawn:", [x.get('type_id', x) if isinstance(x, dict) else x for x in types(W, 'OwningPlayerPawn')][:10])
