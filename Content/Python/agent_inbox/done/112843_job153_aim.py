import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
def Tt(g, f): return [x.get('type_id', x) if isinstance(x, dict) else x for x in types(g, f)]
A = '/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed3.ABP_Unarmed3'
fg = A + ':CalcFlySpeed'
aim = [t for t in Tt(fg, 'BaseAimRotation') if t.endswith('GetBaseAimRotation')]
atan = [t for t in Tt(fg, 'Atan2') if 'Degrees' in t]
fwd = [t for t in Tt(fg, 'GetForwardVector') if 'Rotator' in t or 'Math' in t]
rgt = [t for t in Tt(fg, 'GetRightVector') if 'Rotator' in t or 'Math' in t]
print("ids:", aim, atan, fwd, rgt)
for n_ in nodes(fg):
    if 'FunctionEntry' not in n_: call('delete_node', {'node': {'refPath': n_}})
code = '''(fn CalcFlySpeed ()
  (bind v (Variables|Default|GetVelocity))
  (bind r (%s (Variables|Default|GetCharacter)))
  (bind vf (Math|Vector|DotProduct v (%s r)))
  (bind vr (Math|Vector|DotProduct v (%s r)))
  (bind s (Variables|Default|SetFlySpeed (Math|Vector|VectorLength (Math|Vector|MakeVector vf vr 0.0))))
  (if (Variables|Default|GetIsFlying)
    (Variables|Default|SetGroundSpeed s)
    (Variables|Default|SetDirection (select (< s 10.0) 0.0 (%s vr vf)))))''' % (aim[0], fwd[0], rgt[0], atan[0])
call('write_graph_dsl', {'graph': {'refPath': fg}, 'code': code})
print(str(call('read_graph_dsl', {'graph': {'refPath': fg}})))
try: compile_bp(A); print("compile OK")
except Exception as e: print("compile FAIL", str(e)[:500])
for x in infos(nodes(fg)):
    ex = [(p['name'], [info(c['node']['refPath'])['type_id'] for c in (p.get('connected_pins') or [])]) for p in x['output_pins'] if p['name'] in ('then', 'else')]
    if ex: print("flow", x['type_id'], ex)
