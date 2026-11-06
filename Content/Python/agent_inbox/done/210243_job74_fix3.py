import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
# ---- 1. Sewer entry: decide direction once, before teleporting
E = '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry'
try: call('add_variable', {'blueprint': {'refPath': E}, 'name': 'bGoingDown', 'type_name': 'bool'})
except Exception as e: out.append("var: " + str(e)[:120])
compile_bp(E)
g2 = E + ':UseEntry'
ids = [x.get('type_id', x) if isinstance(x, dict) else x for x in types(g2, 'GoingDown')]
out.append("var nodes: %s" % ids)
SET = [i for i in ids if 'Set' in i.split('|')[-1]][0]; GET = [i for i in ids if 'Get' in i.split('|')[-1]][0]

for n_ in nodes(g2):
    if 'FunctionEntry' not in n_: call('delete_node', {'node': {'refPath': n_}})
call('write_graph_dsl', {'graph': {'refPath': g2}, 'code': '''(fn UseEntry (Player)
  (bind ploc (Transformation|GetActorLocation Player))
  ('''+SET+''' (< (Math|Vector|Distance(Vector) ploc (Transformation|GetWorldLocation (Variables|Default|GetBox))) (Math|Vector|Distance(Vector) ploc (Transformation|GetWorldLocation (Variables|Default|GetSewerBox)))))
  (Transformation|SetActorLocation Player (select ('''+GET+''') (Transformation|GetWorldLocation (Variables|Default|GetCapsule)) (Transformation|GetWorldLocation (Variables|Default|GetReturnPoint))) false true)
  (bind pawn (Utilities|Casting|CastToPawn :Object Player)
    (:then
      (if (Pawn|IsLocallyControlled pawn)
        (CallFunction|ApplySewerView :InSewer ('''+GET+'''))))
    (:CastFailed)))'''})
try: compile_bp(E); out.append("Entry compile OK")
except Exception as e: out.append("Entry compile FAIL " + str(e)[:600])
out.append(str(call('read_graph_dsl', {'graph': {'refPath': g2}})))
# ---- 2. Swap: spawn with the pawn's full transform, no collision nudge
for name in ('CBP_PC_GolKosh', 'CBP_PC_Hope'):
    BP = '/Game/ThirdPerson/Blueprints/%s.%s' % (name, name); EG = BP + ':EventGraph'
    ii = infos(nodes(EG))
    sp = [x for x in ii if x['type_id'].startswith('Game|SpawnActorCBPPC')][0]['node']['refPath']
    st = pin(sp, 'SpawnTransform', 'in')
    feeders = [c['node']['refPath'] for c in (st.get('connected_pins') or [])]
    for f in feeders:
        fi = info(f)
        if fi['type_id'] == 'Math|Conversions|ToTransform(Vector)':
            for c in (pin(f, 'InLocation', 'in').get('connected_pins') or []):
                if info(c['node']['refPath'])['type_id'] == 'Transformation|GetActorLocation':
                    call('delete_node', {'node': c['node']})
            call('delete_node', {'node': {'refPath': f}})
    p = info(sp)['position']
    gt = node(EG, 'Transformation|GetActorTransform', p['x'] - 300, p['y'] + 150)
    connect(pin(gt, 'ReturnValue', 'out'), pin(sp, 'SpawnTransform', 'in'))
    setv(pin(sp, 'CollisionHandlingOverride', 'in'), 'AlwaysSpawn')
    try: compile_bp(BP); out.append(name + " compile OK")
    except Exception as e: out.append(name + " compile FAIL " + str(e)[:600])
    out.append(str(call('read_graph_dsl', {'graph': {'refPath': EG}})).split('(event Custom|S_Swap')[1][:700])
print("\n".join(out))
