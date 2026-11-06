import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
def T(g, f): return [x.get('type_id', x) if isinstance(x, dict) else x for x in types(g, f)]
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
DEG = DN + ':EventGraph'
# --- A. ResyncTime only acts on the server
g = DN + ':ResyncTime'
for n_ in nodes(g):
    if 'FunctionEntry' not in n_: call('delete_node', {'node': {'refPath': n_}})
call('write_graph_dsl', {'graph': {'refPath': g}, 'code': '''(fn ResyncTime ()
  (if (Networking|HasAuthority)
    (CallFunction|SetNetTime :Hour (Variables|Time|GetSolarTime) :Day (Variables|Date|GetDaysOfYear) :Year (Variables|Date|GetYear))))'''})
out.append(str(call('read_graph_dsl', {'graph': {'refPath': g}})))
# --- B. BeginPlay: after MoonIndex -> SetTimer(ResyncTime, 30s, loop) -> ResyncTime -> (timeline as before)
ii = infos(nodes(DEG)); by = {x['node']['refPath']: x for x in ii}
cur = [x for x in ii if x['type_id'] == 'AddEvent|EventBeginPlay'][0]['node']['refPath']
chain = []
for _ in range(10):
    i = by[cur]; chain.append((cur, i['type_id']))
    th = [p for p in i['output_pins'] if p['name'] == 'then']
    if not th or not th[0].get('connected_pins'): break
    cur = th[0]['connected_pins'][0]['node']['refPath']
out.append("BeginPlay chain: %s" % [t for _, t in chain])
mi = [r for r, t in chain if t.endswith('MoonIndex')]
if mi and not any('SetTimer' in t for _, t in chain):
    mi = mi[0]
    nxt_pin = pin(mi, 'then', 'out')['connected_pins'][0]
    nxt = nxt_pin['node']['refPath']
    nxt_in = [p for p in by[nxt]['input_pins'] if p['pin_id'] == nxt_pin.get('pin_id')] or None
    # find which input pin of next node is linked
    linked = [p for p in by[nxt]['input_pins'] if any(c['node']['refPath'] == mi for c in (p.get('connected_pins') or []))][0]
    call('break_pins', {'output_pin': pin(mi, 'then', 'out')['pin_id'], 'input_pin': linked['pin_id']})
    p0 = by[mi]['position']
    st = node(DEG, 'Utilities|Time|SetTimerbyFunctionName', p0['x'] + 250, p0['y'] + 250)
    setv(pin(st, 'FunctionName', 'in'), 'ResyncTime'); setv(pin(st, 'Time', 'in'), '30.0'); setv(pin(st, 'bLooping', 'in'), 'true')
    rs = node(DEG, 'CallFunction|ResyncTime', p0['x'] + 600, p0['y'] + 250)
    connect(pin(mi, 'then', 'out'), pin(st, 'execute', 'in'))
    connect(pin(st, 'then', 'out'), pin(rs, 'execute', 'in'))
    connect(pin(rs, 'then', 'out'), linked)
    out.append("inserted timer + resync before %s.%s" % (by[nxt]['type_id'], linked['name']))
compile_bp(DN)
# --- C. BP_Master_PC: server event with (Hour, Day, Year)
M = '/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC'
MEG = M + ':EventGraph'
if not [x for x in infos(nodes(MEG)) if 'SetTimeSignature_Event' in x['type_id']]:
    d = call('add_event_dispatcher', {'blueprint': {'refPath': M}, 'name': 'SetTimeSignature'})
    dg = d['refPath'] if isinstance(d, dict) else str(d)
    for n_, t_ in (('Hour', 'float'), ('Day', 'int'), ('Year', 'int')):
        call('add_function_param', {'graph': {'refPath': dg}, 'param_name': n_, 'param_type': t_, 'input_param': True})
    compile_bp(M)
    asg = node(MEG, [t for t in T(MEG, 'SetTimeSignature') if t.startswith('Default|Assign')][0], 0, 3000)
    call('delete_node', {'node': {'refPath': asg}})
ev = [x for x in infos(nodes(MEG)) if 'SetTimeSignature_Event' in x['type_id']][0]
evr = ev['node']['refPath']
out.append("server event node: %s pins %s" % (ev['type_id'], [p['name'] for p in ev['output_pins']]))
setnet = [t for t in T(MEG, 'SetNetTime') if 'SetNetTime' in t and not t.startswith('Variables')]
out.append("SetNetTime call types: %s" % setnet)
g3 = call('add_function_graph', {'blueprint': {'refPath': M}, 'graph_name': 'ServerApplyTime'})['refPath']
if len(nodes(g3)) <= 1:
    for n_, t_ in (('Hour', 'float'), ('Day', 'int'), ('Year', 'int')):
        call('add_function_param', {'graph': {'refPath': g3}, 'param_name': n_, 'param_type': t_, 'input_param': True})
    call('write_graph_dsl', {'graph': {'refPath': g3}, 'code': '''(fn ServerApplyTime (Hour Day Year)
  (bind dn (Actor|GetActorOfClass "/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle_C"))
  (if (Utilities|IsValid dn)
    (%s :self dn :Hour Hour :Day Day :Year Year)))''' % setnet[0]})
out.append(str(call('read_graph_dsl', {'graph': {'refPath': g3}})))
th = pin(evr, 'then', 'out')
if not th.get('connected_pins'):
    p0 = ev['position']
    ca = node(MEG, 'CallFunction|ServerApplyTime', p0['x'] + 300, p0['y'])
    connect(th, pin(ca, 'execute', 'in'))
    for n_ in ('Hour', 'Day', 'Year'): connect(pin(evr, n_, 'out'), pin(ca, n_, 'in'))
compile_bp(M)
# --- D. WB_SetTime: route the GetTime message through the player's server event (fallback: local, as before)
W = '/Game/Menus/WB_SetTime.WB_SetTime'
WEG = W + ':EventGraph'
msg = WEG + '.K2Node_Message_2'
mi_ = info(msg)
if not any('Cast' in info(c['node']['refPath'])['type_id'] for p in mi_['input_pins'] if p['name'] == 'execute' for c in (p.get('connected_pins') or [])):
    castT = [t for t in T(WEG, 'CastToBP_Master_PC') if t.endswith('CastToBP_Master_PC')]
    callT = [t for t in T(WEG, 'SetTimeSignature_Event') if 'SetTimeSignature_Event' in t and 'AddEvent' not in t]
    out.append("widget types cast=%s call=%s" % (castT, callT))
    p0 = mi_['position']
    pw = node(WEG, 'Player|GetOwningPlayerPawn', p0['x'] - 400, p0['y'] + 250)
    cs = node(WEG, castT[0], p0['x'] - 200, p0['y'] - 250)
    cl = node(WEG, callT[0], p0['x'] + 150, p0['y'] - 250)
    connect(pin(pw, 'ReturnValue', 'out'), pin(cs, 'Object', 'in'))
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
print("\n".join(out))
