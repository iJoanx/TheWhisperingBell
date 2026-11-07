import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
BPS = ['/Game/Menus/WB_SetTime.WB_SetTime', '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle']
for bp in BPS:
    for g in call('list_graphs', {'blueprint': {'refPath': bp}}):
        try:
            for x in infos(nodes(g['refPath'])):
                if 'LeapYear' in x['type_id']:
                    out.append("NODE %s [%s]" % (x['node']['refPath'], x['type_id']))
                    for p in x['input_pins'] + x['output_pins']:
                        out.append("   pin %s" % json.dumps(p)[:700])
        except Exception as e: out.append("graph %s err %s" % (g['refPath'], str(e)[:200]))
G = BPS[0] + ':EventGraph'
for flt in ('%(Integer)', '==(Integer)', 'EqualEqual', 'Integer|=='):
    try: out.append("%s -> %s" % (flt, [x.get('type_id') if isinstance(x, dict) else x for x in types(G, flt)][:15]))
    except Exception as e: out.append("%s ERR %s" % (flt, str(e)[:200]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump163.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
