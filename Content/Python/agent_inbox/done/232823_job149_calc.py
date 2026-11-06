import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
A = '/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed3.ABP_Unarmed3'
fg = A + ':CalcFlySpeed'
for n_ in nodes(fg):
    if 'FunctionEntry' not in n_: call('delete_node', {'node': {'refPath': n_}})
call('write_graph_dsl', {'graph': {'refPath': fg}, 'code': '''(fn CalcFlySpeed ()
  (bind v (Variables|Default|GetVelocity))
  (bind c (Variables|Default|GetCharacter))
  (bind s (Variables|Default|SetFlySpeed (Math|Vector|VectorLength (Math|Vector|MakeVector (Math|Vector|DotProduct v (Transformation|GetActorForwardVector c)) (Math|Vector|DotProduct v (Transformation|GetActorRightVector c)) 0.0))))
  (if (Variables|Default|GetIsFlying)
    (Variables|Default|SetGroundSpeed s)))'''})
print(str(call('read_graph_dsl', {'graph': {'refPath': fg}})))
EG = A + ':EventGraph'
seq = [x for x in infos(nodes(EG)) if 'Sequence' in x['type_id']]
for x in seq:
    print("sequence", x['node']['refPath'].split('.')[-1], [(p['name'], [info(c['node']['refPath'])['type_id'] for c in (p.get('connected_pins') or [])]) for p in x['output_pins']])
try: compile_bp(A); print("compile OK")
except Exception as e: print("compile FAIL", str(e)[:500])
