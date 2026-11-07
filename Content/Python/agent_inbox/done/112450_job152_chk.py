import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
fg = '/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed3.ABP_Unarmed3:CalcFlySpeed'
for x in infos(nodes(fg)):
    ex = [(p['name'], [info(c['node']['refPath'])['type_id'] for c in (p.get('connected_pins') or [])]) for p in x['output_pins'] if p['name'] in ('then', 'else', 'execute')]
    if ex: print(x['type_id'], ex)
