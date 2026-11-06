import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
def Tt(g, f): return [x.get('type_id', x) if isinstance(x, dict) else x for x in types(g, f)]
out = []
B = '/Game/ThirdPerson/Blueprints/CBP_Familiar_Bolita.CBP_Familiar_Bolita'
EG = B + ':EventGraph'
have = call('list_variables', {'blueprint': {'refPath': B}})
for v in ('bFlyUp', 'bFlyDown'):
    if v not in have: call('add_variable', {'blueprint': {'refPath': B}, 'name': v, 'type_name': 'bool'})
compile_bp(B)
ids = Tt(EG, 'FlyUp') + Tt(EG, 'FlyDown')
out.append("var nodes: %s" % ids)
g = lambda n: [i for i in ids if i.endswith('|Get' + n)][0]
s = lambda n: [i for i in ids if i.endswith('|Set' + n)][0]
up = 'FlyUp' if any(i.endswith('|GetFlyUp') for i in ids) else 'bFlyUp'
dn = 'FlyDown' if any(i.endswith('|GetFlyDown') for i in ids) else 'bFlyDown'
fg = call('add_function_graph', {'blueprint': {'refPath': B}, 'graph_name': 'FlyVertical'})['refPath']
for n_ in nodes(fg):
    if 'FunctionEntry' not in n_: call('delete_node', {'node': {'refPath': n_}})
call('write_graph_dsl', {'graph': {'refPath': fg}, 'code': '''(fn FlyVertical ()
  (if (Movement|IsFlying (Variables|Character|GetCharacterMovement))
    (Pawn|Input|AddMovementInput :WorldDirection "0, 0, 1" :ScaleValue (- (Math|Conversions|ToFloat(Boolean) (%s)) (Math|Conversions|ToFloat(Boolean) (%s))))))''' % (g(up), g(dn))})
out.append(str(call('read_graph_dsl', {'graph': {'refPath': fg}})))
ii = infos(nodes(EG))
if not [x for x in ii if x['type_id'] in ('Input|KeyboardEvents|E', 'Input|KeyboardEvents|Q')]:
    tick = [x for x in ii if x['type_id'] == 'AddEvent|EventTick'][0]
    p = tick['position']
    fv = node(EG, 'CallFunction|FlyVertical', p['x'] + 300, p['y'])
    connect(pin(tick['node']['refPath'], 'then', 'out'), pin(fv, 'execute', 'in'))
    y = p['y'] + 250
    for key, var in (('E', up), ('Q', dn)):
        k = node(EG, 'Input|KeyboardEvents|' + key, p['x'], y)
        on = node(EG, s(var), p['x'] + 300, y); off = node(EG, s(var), p['x'] + 300, y + 120)
        bpin = lambda n: [q for q in info(n)['input_pins'] if q['name'] not in ('execute', 'self')][0]
        setv(bpin(on), 'true'); setv(bpin(off), 'false')
        connect(pin(k, 'Pressed', 'out'), pin(on, 'execute', 'in'))
        connect(pin(k, 'Released', 'out'), pin(off, 'execute', 'in'))
        y += 300
try: compile_bp(B); out.append("compile OK")
except Exception as e: out.append("compile FAIL " + str(e)[:600])
d = str(call('read_graph_dsl', {'graph': {'refPath': EG}}))
for key in ('(event EventTick', '(event E ', '(event Q '):
    i = d.find(key); out.append(d[i:i + 300] if i >= 0 else key + ' missing')
print("\n".join(out))
