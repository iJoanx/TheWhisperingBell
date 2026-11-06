import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
EG = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope:EventGraph'
cur = EG + '.K2Node_CallFunction_11'
chain = []
for _ in range(6):
    i = info(cur); chain.append(i['type_id'])
    t = [p for p in i['output_pins'] if p['name'] in ('then',)]
    if not t or not t[0].get('connected_pins'): break
    cur = t[0]['connected_pins'][0]['node']['refPath']
print(" -> ".join(chain))
d = [p for p in info([n for n in nodes(EG) if 'DoTeleport' in info(n)['type_id']][0])['input_pins'] if p['name'] == 'Dest'][0]
print("Dest from", [c['node']['refPath'].split('.')[-1] for c in d.get('connected_pins') or []])
print("MC_Teleportcompleted left:", [n for n in nodes(EG) if 'Teleportcompleted' in info(n)['type_id']])
