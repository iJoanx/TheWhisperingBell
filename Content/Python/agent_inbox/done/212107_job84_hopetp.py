import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
H = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope'
EG = H + ':EventGraph'
N = lambda n: EG + '.' + n
# b) (continuing) reuse the DoTeleport call node made last time
ex = [x for x in infos(nodes(EG)) if 'DoTeleport' in x['type_id']]
out.append("existing DoTeleport calls: %d" % len(ex))
s_call = N('K2Node_CallFunction_2')
p = info(s_call)['position']
dt1 = ex[0]['node']['refPath'] if ex else node(EG, 'CallFunction|DoTeleport', p['x'], p['y'] + 200)
cp = N('K2Node_CallFunction_23')   # reuse the existing C_PlayMontage call, detached from the old multicast chain
for c in (pin(cp, 'execute', 'in').get('connected_pins') or []):
    call('break_pins', {'output_pin': c['pin_id'], 'input_pin': pin(cp, 'execute', 'in')['pin_id']})
connect(pin(N('K2Node_CallFunction_11'), 'then', 'out'), pin(dt1, 'execute', 'in'))
connect(pin(N('K2Node_PromotableOperator_3'), 'ReturnValue', 'out'), pin(dt1, 'Dest', 'in'))
connect(pin(dt1, 'then', 'out'), pin(cp, 'execute', 'in'))
connect(pin(cp, 'then', 'out'), pin(s_call, 'execute', 'in'))
out.append(str(call('read_graph_dsl', {'graph': {'refPath': H + ':DoTeleport'}})))
# c) server: repeat the move unless it's the host's own pawn (already moved)
call('delete_node', {'node': {'refPath': N('K2Node_CallFunction_3')}})
ev = N('K2Node_CustomEvent_7'); q = info(ev)['position']
br = node(EG, 'Utilities|FlowControl|Branch', q['x'] + 300, q['y'])
il = node(EG, 'Pawn|IsLocallyControlled', q['x'] + 100, q['y'] + 150)
dt2 = node(EG, 'CallFunction|DoTeleport', q['x'] + 600, q['y'] + 50)
connect(pin(ev, 'then', 'out'), pin(br, 'execute', 'in'))
connect(pin(il, 'ReturnValue', 'out'), pin(br, 'Condition', 'in'))
connect(pin(br, 'else', 'out'), pin(dt2, 'execute', 'in'))
connect(pin(ev, 'TrueDestination', 'out'), pin(dt2, 'Dest', 'in'))
# d) remove the old multicast teleport (it re-teleported every machine, zeroed velocity and replayed the montage)
for n in ('K2Node_CustomEvent_1', 'K2Node_CallFunction_22', 'K2Node_CallFunction_15', 'K2Node_VariableGet_12'):
    call('delete_node', {'node': {'refPath': N(n)}})
try: compile_bp(H); out.append("compile OK")
except Exception as e: out.append("compile FAIL " + str(e)[:800])
d = str(call('read_graph_dsl', {'graph': {'refPath': EG}}))
for key in ('(event EnhancedInputActionIA_Aim', '(event Custom|S_TeleportCompleted', '(event Custom|C_PlayMontage', '(event Custom|MC_PlayMontage'):
    i = d.find(key); out.append(d[i:i+900] if i >= 0 else key + " missing")
print("\n".join(out))
