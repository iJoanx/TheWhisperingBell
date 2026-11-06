import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
def T(g, f): return [x.get('type_id', x) if isinstance(x, dict) else x for x in types(g, f)]
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
DEG = DN + ':EventGraph'
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
M = '/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC'
for v in ('NetTime_0', 'NetTime_1'):
    try: call('remove_variable', {'blueprint': {'refPath': DN}, 'name': v}); out.append('removed ' + v)
    except Exception as e: out.append('remove %s: %s' % (v, str(e)[:150]))
out.append('DN vars: %s' % [x for x in call('list_variables', {'blueprint': {'refPath': DN}}) if 'Net' in x])
# --- D. WB_SetTime: route the GetTime message through the player's server event (fallback: local, as before)
W = '/Game/Menus/WB_SetTime.WB_SetTime'
WEG = W + ':EventGraph'
msg = WEG + '.K2Node_Message_2'
mi_ = info(msg)
if not any('Cast' in info(c['node']['refPath'])['type_id'] for p in mi_['input_pins'] if p['name'] == 'execute' for c in (p.get('connected_pins') or [])):
    p0 = mi_['position']
    pw = WEG + '.K2Node_CallFunction_45'
    cs = WEG + '.K2Node_DynamicCast_0'
    if not pin(cs, 'Object', 'in').get('connected_pins'): connect(pin(pw, 'ReturnValue', 'out'), pin(cs, 'Object', 'in'))
    cl = node(WEG, 'Class|BPMasterPC|SetTimeSignatureEvent', p0['x'] + 150, p0['y'] - 250)
    ex = [p for p in mi_['input_pins'] if p['name'] == 'execute'][0]
    srcs = [c for c in (ex.get('connected_pins') or [])]
    for c in srcs:
        sp = [p for p in info(c['node']['refPath'])['output_pins'] if any(cc['node']['refPath'] == msg for cc in (p.get('connected_pins') or []))]
        for s_ in sp:
            call('break_pins', {'output_pin': s_['pin_id'], 'input_pin': ex['pin_id']})
            connect(s_, pin(cs, 'execute', 'in'))
    connect(pin(cs, 'CastFailed', 'out'), pin(msg, 'execute', 'in'))
    connect(pin(cs, 'then', 'out'), pin(cl, 'execute', 'in'))
    asP = [p for p in info(cs)['output_pins'] if p['name'].startswith('As')][0]
    connect(asP, pin(cl, 'self', 'in'))
    for n_ in ('Hour', 'Day', 'Year'):
        src = [p for p in mi_['input_pins'] if p['name'] == n_][0]
        for c in (src.get('connected_pins') or []):
            op = [p for p in info(c['node']['refPath'])['output_pins'] if any(cc['node']['refPath'] == msg for cc in (p.get('connected_pins') or []))]
            for o_ in op: connect(o_, pin(cl, n_, 'in'))
    mthen = pin(msg, 'then', 'out')
    for c in (mthen.get('connected_pins') or []):
        tgt = [p for p in info(c['node']['refPath'])['input_pins'] if any(cc['node']['refPath'] == msg for cc in (p.get('connected_pins') or []))]
        for t_ in tgt: connect(pin(cl, 'then', 'out'), t_)
    out.append("widget rewired: %d exec sources" % len(srcs))
for b in (DN, M, W):
    try: compile_bp(b); out.append("compiled OK " + b.split('.')[-1])
    except Exception as e: out.append("COMPILE FAIL %s %s" % (b.split('.')[-1], str(e)[:500]))
out.append(str(call('read_graph_dsl', {'graph': {'refPath': WEG}}))[-1800:])
print("\n".join(out))
