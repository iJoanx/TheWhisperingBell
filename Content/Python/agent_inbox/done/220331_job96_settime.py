import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
def scan(bp, keys):
    for g in call('list_graphs', {'blueprint': {'refPath': bp}}):
        d = str(call('read_graph_dsl', {'graph': {'refPath': g['refPath']}}))
        for blk in d.split("\n\n"):
            if any(k in blk for k in keys):
                out.append("--- %s\n%s" % (g['refPath'].split(':')[-1], blk[:2500]))
scan('/Game/Menus/WB_SetTime.WB_SetTime', ['GetTime', 'SetTime', 'DayNight', 'SolarTime', 'Hour', 'Event'])
scan('/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC', ['GetTime', 'SetTime', 'DayNight', 'SolarTime', 'WB_SetTime'])
scan('/Game/ThirdPerson/Blueprints/BP_Master_Familiar.BP_Master_Familiar', ['GetTime', 'SetTime', 'DayNight', 'SolarTime'])
for bpi in ('/Game/Menus/BPI_SetTime.BPI_SetTime', '/Game/Level/WhisperingBell/Blueprints/BPI_SolarTime.BPI_SolarTime'):
    try: out.append("BPI %s graphs %s" % (bpi, [g['refPath'].split(':')[-1] for g in call('list_graphs', {'blueprint': {'refPath': bpi}})]))
    except Exception as e: out.append("bpi err %s" % e)
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump96.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
