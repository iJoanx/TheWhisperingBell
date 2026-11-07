import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
bp = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
for g in call('list_graphs', {'blueprint': {'refPath': bp}}):
    try:
        d = str(call('read_graph_dsl', {'graph': {'refPath': g['refPath']}}))
        out.append("=== GRAPH %s\n%s" % (g['refPath'].split(':')[-1], d))
    except Exception as e: out.append("=== GRAPH %s ERR %s" % (g['refPath'], e))
try: out.append("parent: %s" % unreal.load_asset('/Game/NightSky/BP_DayNightCycle').get_editor_property('parent_class'))
except Exception as e: out.append("parent err %s" % e)
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump168.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
