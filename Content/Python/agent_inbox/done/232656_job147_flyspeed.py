import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
def Tt(g, f): return [x.get('type_id', x) if isinstance(x, dict) else x for x in types(g, f)]
out = []
A = '/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed3.ABP_Unarmed3'
EG = A + ':EventGraph'
if 'FlySpeed' not in call('list_variables', {'blueprint': {'refPath': A}}):
    call('add_variable', {'blueprint': {'refPath': A}, 'name': 'FlySpeed', 'type_name': 'float'})
compile_bp(A)
fg = call('add_function_graph', {'blueprint': {'refPath': A}, 'graph_name': 'CalcFlySpeed'})['refPath']
for n_ in nodes(fg):
    if 'FunctionEntry' not in n_: call('delete_node', {'node': {'refPath': n_}})
call('write_graph_dsl', {'graph': {'refPath': fg}, 'code': '''(fn CalcFlySpeed ()
  (bind v (Variables|Default|GetVelocity))
  (bind c (Variables|Default|GetCharacter))
  (Variables|Default|SetFlySpeed (Math|Vector|VectorLength (Math|Vector|MakeVector (Math|Vector|DotProduct v (Transformation|GetActorForwardVector c)) (Math|Vector|DotProduct v (Transformation|GetActorRightVector c)) 0.0))))'''})
out.append(str(call('read_graph_dsl', {'graph': {'refPath': fg}})))
# append to the end of Update Animation
ii = infos(nodes(EG)); by = {x['node']['refPath']: x for x in ii}
cur = [x for x in ii if x['type_id'] == 'AddEvent|EventBlueprintUpdateAnimation'][0]['node']['refPath']
for _ in range(30):
    th = [p for p in by[cur]['output_pins'] if p['name'] == 'then']
    if not th or not th[0].get('connected_pins'): break
    cur = th[0]['connected_pins'][0]['node']['refPath']
ex = [x for x in infos(nodes(EG)) if x['type_id'].endswith('CalcFlySpeed')]
cf = ex[0]['node']['refPath'] if ex else node(EG, 'CallFunction|CalcFlySpeed', by[cur]['position']['x'] + 350, by[cur]['position']['y'] + 400)
if not pin(cf, 'execute', 'in').get('connected_pins'):
    if 'Sequence' in by[cur]['type_id']:
        call('add_node_pin', {'node': {'refPath': cur}})
        outs = [p for p in info(cur)['output_pins'] if p['name'].startswith('then_')]
        free = [p for p in outs if not p.get('connected_pins')]
        connect(free[-1], pin(cf, 'execute', 'in'))
        out.append("CalcFlySpeed on new sequence pin %s" % free[-1]['name'])
    else:
        connect(pin(cur, 'then', 'out'), pin(cf, 'execute', 'in'))
        out.append("appended after %s" % by[cur]['type_id'])
# Fly state: Y input = FlySpeed instead of GroundSpeed
FS = [x['refPath'] for x in call('list_graphs', {'blueprint': {'refPath': A}}) if x['refPath'].endswith('.Fly')][0]
bsn = [x for x in infos(nodes(FS)) if 'BlendspacePlayer' in x['type_id']][0]['node']['refPath']
old = [x for x in infos(nodes(FS)) if x['type_id'].endswith('GetGroundSpeed')]
getT = [t for t in Tt(FS, 'FlySpeed') if t.endswith('|GetFlySpeed')]
out.append("getter types: %s" % getT)
gp = node(FS, getT[0], -300, 150)
connect(info(gp)['output_pins'][0], pin(bsn, 'Y', 'in'))
for x in old: call('delete_node', {'node': x['node']})
try: compile_bp(A); out.append("compile OK")
except Exception as e: out.append("compile FAIL " + str(e)[:600])
out.append(dumpnodes(FS))
print("\n".join(out))
