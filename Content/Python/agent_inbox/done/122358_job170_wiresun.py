import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
try: out.append("compile first: %s" % str(compile_bp(DN))[:400])
except Exception as e: out.append("compile err %s" % str(e)[:400])
for G in (DN + ':UpdateSun', DN + ':IsDST'):
    for x in infos(nodes(G)):
        if x['type_id'] not in ('SunPosition|GetSunPosition', 'Math|DateTime|MakeDateTime'): continue
        yp = [p for p in x['input_pins'] if p['name'] == 'Year'][0]
        pos = x.get('position') or {'x': 0, 'y': 0}
        try:
            s = node(G, 'CallFunction|GetSunYear', pos.get('x', 0) - 260, pos.get('y', 0) + 80)
            si = info(s)
            if any(p['type_id'] == 'Exec' or p['name'] in ('execute', 'then') for p in si['input_pins'] + si['output_pins']):
                out.append("WARNING: GetSunYear node still has exec pins (not pure?) %s" % [p['name'] for p in si['input_pins'] + si['output_pins']])
            so = [p for p in si['output_pins'] if p['name'] == 'SunYear'][0]
            for c in (yp.get('connected_pins') or []):
                call('break_pins', {'output_pin': c, 'input_pin': yp['pin_id']})
            connect(so, yp)
            out.append("wired %s" % x['node']['refPath'].split(':')[-1])
        except Exception as e: out.append("FAIL %s %s" % (x['node']['refPath'], str(e)[:500]))
# remove Year getters / knots left unconnected
for G in (DN + ':UpdateSun', DN + ':IsDST'):
    for x in infos(nodes(G)):
        if ('GetYear' in x['type_id'] or 'Knot' in x['node']['refPath']) and not any(p.get('connected_pins') for p in x['output_pins']):
            call('delete_node', {'node': {'refPath': x['node']['refPath']}}); out.append("removed dangling " + x['node']['refPath'].split(':')[-1])
try: out.append("compile: %s" % str(compile_bp(DN))[:800])
except Exception as e: out.append("compile err %s" % str(e)[:800])
for fn in ('UpdateSun', 'IsDST'):
    out.append("--- %s\n%s" % (fn, str(call('read_graph_dsl', {'graph': {'refPath': DN + ':' + fn}}))[:2500]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump170.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
