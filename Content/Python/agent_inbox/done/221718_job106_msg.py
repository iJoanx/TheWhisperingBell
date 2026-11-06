import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
W = '/Game/Menus/WB_SetTime.WB_SetTime:EventGraph'
i = info(W + '.K2Node_Message_2'); print("widget message type:", i['type_id'], [p['name'] for p in i['input_pins']])
EG = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle:EventGraph'
for f in ('Interface', 'Message', 'SetTime', 'BPI'):
    ids = [x.get('type_id', x) if isinstance(x, dict) else x for x in types(EG, f)]
    print(f, [t for t in ids if 'Time' in t][:20])
