import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
H = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope:EventGraph'
for f in ('Velocity', 'MakeVector', 'LaunchCharacter'):
    ids = [x.get('type_id', x) if isinstance(x, dict) else x for x in types(H, f)]
    print(f, ids[:40])
for t in ('Variables|CharacterMovement|SetVelocity', 'Variables|Velocity|SetVelocity'):
    try: print(t, tpins(H, t))
    except Exception as e: print(t, "no")
