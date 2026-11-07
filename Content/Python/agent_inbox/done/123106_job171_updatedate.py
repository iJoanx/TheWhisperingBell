import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
G = DN + ':UpdateDate'
def tl(f):
    return [x.get('type_id') if isinstance(x, dict) else x for x in types(G, f)]
SUB = next((t for t in tl('Subtract') if t.startswith('Utilities|Operators|Subtract')), None)
GETV = next((t for t in tl('GetDaysinMonths') if t.endswith('GetDaysinMonths')), None)
out.append("SUB=%s GETV=%s" % (SUB, GETV))
dim = [x for x in infos(nodes(G)) if x['type_id'] == 'Math|DateTime|DaysInMonth']
out.append("DaysInMonth nodes: %d" % len(dim))
if SUB and GETV and len(dim) == 1:
    x = dim[0]; ref = x['node']['refPath']
    pos = x.get('position') or {'x': 0, 'y': 0}; px, py = pos.get('x', 0), pos.get('y', 0)
    msrc = [p for p in x['input_pins'] if p['name'] == 'Month'][0]['connected_pins'][0]
    dsts = [p for p in x['output_pins'] if p['name'] == 'ReturnValue'][0]['connected_pins']
    try:
        gv = node(G, GETV, px - 200, py - 60)
        gi = node(G, 'Utilities|Array|Get(aref)', px, py)
        sb = node(G, SUB, px - 200, py + 60)
        connect({'pin_id': msrc}, info(sb)['input_pins'][0])
        setv(info(sb)['input_pins'][1], 1)
        connect(info(gv)['output_pins'][0], info(gi)['input_pins'][0])
        connect(info(sb)['output_pins'][0], info(gi)['input_pins'][1])
        call('delete_node', {'node': {'refPath': ref}})
        go = info(gi)['output_pins'][0]
        out.append("get out pin %s:%s" % (go['name'], go['type_id']))
        for d in dsts: connect(go, {'pin_id': d})
        for y in infos(nodes(G)):
            if 'GetYear' in y['type_id'] and not any(p.get('connected_pins') for p in y['output_pins']):
                call('delete_node', {'node': {'refPath': y['node']['refPath']}}); out.append("removed dangling " + y['node']['refPath'].split(':')[-1])
        out.append("rewired ok")
    except Exception as e: out.append("FAIL %s" % str(e)[:800])
    try: out.append("compile: %s" % str(compile_bp(DN))[:800])
    except Exception as e: out.append("compile err %s" % str(e)[:800])
out.append(str(call('read_graph_dsl', {'graph': {'refPath': G}}))[:2000])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump171.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
