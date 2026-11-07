import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
BPS = ['/Game/Menus/WB_SetTime.WB_SetTime', '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle']
# find the type id of an integer == node already in use
EQ = None
for x in infos(nodes(BPS[0] + ':SetHolidays')):
    if x['type_id'].endswith('==') or '|==' in x['type_id'] or 'EqualEqual' in x['type_id']:
        EQ = x['type_id']; break
out.append("EQ type: %s" % EQ)
if EQ is None:
    for x in infos(nodes(BPS[0] + ':SetHolidays')): out.append("  t %s" % x['type_id'])
else:
  for bp in BPS:
    for g in call('list_graphs', {'blueprint': {'refPath': bp}}):
        G = g['refPath']
        try: xs = infos(nodes(G))
        except Exception: continue
        for x in xs:
            if x['type_id'] != 'Math|DateTime|IsLeapYear': continue
            ref = x['node']['refPath']
            try:
                pos = x.get('position') or {'x': 0, 'y': 0}
                px, py = pos.get('x', 0), pos.get('y', 0)
                yin = [p for p in x['input_pins'] if p['name'] == 'Year'][0]
                rv = [p for p in x['output_pins'] if p['name'] == 'ReturnValue'][0]
                src = yin['connected_pins'][0]
                dsts = rv['connected_pins']
                m = node(G, 'Math|Integer|%(Integer)', px, py)
                mi = info(m)
                mA, mB = mi['input_pins'][0], mi['input_pins'][1]
                connect({'pin_id': src}, mA); setv(mB, 4)
                e = node(G, EQ, px + 160, py)
                ei = info(e)
                connect(mi['output_pins'][0], ei['input_pins'][0])
                ei = info(e)
                setv(ei['input_pins'][1], 0)
                call('delete_node', {'node': {'refPath': ref}})
                eo = [p for p in info(e)['output_pins'] if p['type_id'] == 'Boolean'][0]
                for d in dsts: connect(eo, {'pin_id': d})
                out.append("fixed %s (mod pins %s, eq pins %s)" % (ref.split(':')[-1] if False else ref, [p['name'] for p in mi['input_pins']], [p['name'] + ':' + p['type_id'] for p in info(e)['input_pins']]))
            except Exception as ex:
                out.append("FAIL %s: %s" % (ref, str(ex)[:600]))
    try: out.append("compile %s: %s" % (bp, str(compile_bp(bp))[:600]))
    except Exception as ex: out.append("compile err %s %s" % (bp, str(ex)[:600]))
  for bp, fns in ((BPS[0], ('DayOfYear', 'DayToMonth', 'SetHolidays')), (BPS[1], ('UpdateDayOfYear', 'SetDate', 'MoonIndex'))):
    for fn in fns:
        d = str(call('read_graph_dsl', {'graph': {'refPath': bp + ':' + fn}}))
        out.append("--- %s\n%s" % (fn, "\n".join(l for l in d.split("\n") if '%' in l or 'LeapYear' in l)[:600]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump164.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
