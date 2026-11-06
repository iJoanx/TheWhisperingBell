import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
EG = '/Game/ThirdPerson/Blueprints/CBP_Familiar_Bolita.CBP_Familiar_Bolita:EventGraph'
for x in infos(nodes(EG)):
    if x['type_id'] in ('Input|KeyboardEvents|E', 'Input|KeyboardEvents|Q'):
        for p in x['output_pins']:
            if p['name'] in ('Pressed', 'Released'):
                for c in (p.get('connected_pins') or []):
                    t = info(c['node']['refPath'])
                    val = [q.get('default_value') for q in t['input_pins'] if q['name'] not in ('execute', 'self')]
                    print(x['type_id'].split('|')[-1], p['name'], '->', t['type_id'], val)
