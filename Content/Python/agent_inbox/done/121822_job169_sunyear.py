import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
names = [g['refPath'].split(':')[-1] for g in call('list_graphs', {'blueprint': {'refPath': DN}})]
if 'GetSunYear' in names:
    out.append("GetSunYear exists already"); g = DN + ':GetSunYear'
else:
    g = call('add_function_graph', {'blueprint': {'refPath': DN}, 'graph_name': 'GetSunYear'})['refPath']
    try: out.append("param: %s" % call('add_function_param', {'graph': {'refPath': g}, 'param_name': 'SunYear', 'param_type': 'int', 'input_param': False}))
    except Exception as e: out.append("param err %s" % str(e)[:400])
    DSL = """(fn GetSunYear ()
  (bind y (Variables|Date|GetYear))
  (if (and (and (>= y 1) (<= y 9999)) (not (and (and (== (Variables|Date|GetMonth) 2) (== (Variables|Date|GetDay) 29)) (not (Math|DateTime|IsLeapYear y)))))
    (return y)
    (else
      (return (+ 2000 (Math|Integer|%(Integer) (+ (Math|Integer|%(Integer) y 100) 100) 100))))))"""
    try: out.append("write: %s" % str(call('write_graph_dsl', {'graph': {'refPath': g}, 'code': DSL}))[:800])
    except Exception as e: out.append("write err %s" % str(e)[:1500])
# try to make it pure
for x in infos(nodes(g)):
    if 'FunctionEntry' in x['node']['refPath'] or 'Entry' in x['type_id']:
        ref = x['node']['refPath']
        try:
            cur = getprops(ref, ['ExtraFlags']); out.append("entry flags before %s" % cur)
            val = cur['ExtraFlags'] if isinstance(cur, dict) and 'ExtraFlags' in cur else 0
            try: val = int(val)
            except Exception: val = 0
            out.append("set pure: %s" % setprops(ref, {'ExtraFlags': val | 0x10000000}))
            out.append("entry flags after %s" % getprops(ref, ['ExtraFlags']))
        except Exception as e: out.append("pure err %s" % str(e)[:500])
try: out.append("compile: %s" % str(compile_bp(DN))[:800])
except Exception as e: out.append("compile err %s" % str(e)[:800])
out.append("READBACK:\n" + str(call('read_graph_dsl', {'graph': {'refPath': g}})))
for G in (DN + ':UpdateSun', DN + ':IsDST'):
    try: out.append("%s types: %s" % (G, [x.get('type_id') if isinstance(x, dict) else x for x in types(G, 'GetSunYear')]))
    except Exception as e: out.append("types err %s" % str(e)[:300])
    for x in infos(nodes(G)):
        if x['type_id'] in ('SunPosition|GetSunPosition', 'Math|DateTime|MakeDateTime'):
            for p in x['input_pins']:
                if p['name'] == 'Year': out.append("  %s Year <- %s" % (x['node']['refPath'].split(':')[-1], p.get('connected_pins')))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump169.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
