import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
def Tt(g, f): return [x.get('type_id', x) if isinstance(x, dict) else x for x in types(g, f)]
EG = '/Game/ThirdPerson/Blueprints/CBP_Familiar_Bolita.CBP_Familiar_Bolita:EventGraph'
for f in ('KeyboardEvents|E', 'KeyboardEvents|Q', 'IsFlying', 'AddMovementInput', 'ToFloat(Boolean)'):
    print(f, Tt(EG, f)[:12])
print(dumpnodes(EG))
