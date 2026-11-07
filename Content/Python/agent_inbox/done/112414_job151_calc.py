import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
A = '/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed3.ABP_Unarmed3'
fg = A + ':CalcFlySpeed'
for n_ in nodes(fg):
    if 'FunctionEntry' not in n_: call('delete_node', {'node': {'refPath': n_}})
call('write_graph_dsl', {'graph': {'refPath': fg}, 'code': '''(fn CalcFlySpeed ()
  (bind s (Variables|Default|SetFlySpeed (Math|Vector|VectorLength (Variables|Default|GetVelocity))))
  (if (Variables|Default|GetIsFlying)
    (Variables|Default|SetGroundSpeed s)
    (if (< (Math|Vector|VectorLengthXY (Variables|Default|GetVelocity)) 50.0)
      (Variables|Default|SetDirection 0.0))))'''})
print(str(call('read_graph_dsl', {'graph': {'refPath': fg}})))
try: compile_bp(A); print("compile OK")
except Exception as e: print("compile FAIL", str(e)[:500])
