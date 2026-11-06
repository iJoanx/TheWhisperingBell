import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
B = '/Game/ThirdPerson/Blueprints/CBP_Familiar_Bolita.CBP_Familiar_Bolita'; EG = B + ':EventGraph'
for x in infos(nodes(EG)):
    if x['type_id'] in ('Input|KeyboardEvents|E', 'Input|KeyboardEvents|Q'):
        for p in x['output_pins']:
            if p['name'] in ('Pressed', 'Released'):
                for c in (p.get('connected_pins') or []):
                    t = info(c['node']['refPath'])
                    vp = [q for q in t['input_pins'] if q['name'] not in ('execute', 'self')][0]
                    want = 'true' if p['name'] == 'Pressed' else 'false'
                    setv(vp, want)
                    got = call('get_pin_value', {'pin': vp['pin_id']})
                    print(x['type_id'].split('|')[-1], p['name'], t['type_id'], vp['name'], '=', got)
compile_bp(B); print("compile OK")
