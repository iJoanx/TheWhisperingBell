import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
H = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope'
G = H + ':GetTeleportTraceCapsule'
LOCALS = [('CamLoc', 'Vector'), ('AimEnd', 'Vector'), ('AimHit', 'bool'), ('AimPoint', 'Vector'), ('AimNormal', 'Vector'),
          ('SurfaceUp', 'float'), ('Spot', 'Vector')]
for n, t in LOCALS:
    try: call('add_variable', {'blueprint': {'refPath': H}, 'name': n, 'type_name': t, 'graph': {'refPath': G}}); out.append("local " + n)
    except Exception as e: out.append("local %s err %s" % (n, str(e)[:300]))
try: compile_bp(H)
except Exception as e: out.append("compile " + str(e)[:300])
for f in ('CamLoc', 'Spot', 'omment'):
    try: out.append("TYPES %s: %s" % (f, [c.get('type_id') if isinstance(c, dict) else c for c in types(G, f)][:30]))
    except Exception as e: out.append("types err " + str(e)[:300])
for f in ('find_node_categories',):
    try: out.append(str(call(f, {'graph': {'refPath': G}}))[:1500])
    except Exception as e: out.append(f + " err " + str(e)[:400])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump328.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
