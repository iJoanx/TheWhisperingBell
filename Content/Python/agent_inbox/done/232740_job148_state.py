import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
A = '/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed3.ABP_Unarmed3'
EG = A + ':EventGraph'
print("CalcFlySpeed calls in EventGraph:", [(x['node']['refPath'].split('.')[-1], bool(pin(x['node']['refPath'], 'execute', 'in').get('connected_pins'))) for x in infos(nodes(EG)) if x['type_id'].endswith('CalcFlySpeed')])
FS = [x['refPath'] for x in call('list_graphs', {'blueprint': {'refPath': A}}) if x['refPath'].endswith('.Fly')][0]
bsn = [x for x in infos(nodes(FS)) if 'BlendspacePlayer' in x['type_id']][0]['node']['refPath']
gp = None
for t in ('Variables|Default|GetFlySpeed', '|GetFlySpeed', 'Variables|GetFlySpeed'):
    try: gp = node(FS, t, -300, 150); print("created", t); break
    except Exception as e: print("no", t, str(e)[:80])
if gp:
    for x in infos(nodes(FS)):
        if x['type_id'].endswith('GetGroundSpeed'): call('delete_node', {'node': x['node']})
    connect(info(gp)['output_pins'][0], pin(bsn, 'Y', 'in'))
try: compile_bp(A); print("compile OK")
except Exception as e: print("compile FAIL", str(e)[:500])
print(dumpnodes(FS))
print(str(call('read_graph_dsl', {'graph': {'refPath': A + ':CalcFlySpeed'}})))
