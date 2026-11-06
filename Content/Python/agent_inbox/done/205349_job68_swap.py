import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
def fix(name):
    BP = '/Game/ThirdPerson/Blueprints/%s.%s' % (name, name)
    EG = BP + ':EventGraph'
    ii = infos(nodes(EG))
    T = lambda t: [x for x in ii if x['type_id'] == t]
    s_ev = T('AddEvent|Custom|S_Swap'); m_ev = T('AddEvent|Custom|M_Swap')
    spawn = [x for x in ii if x['type_id'].startswith('Game|SpawnActorCBPPC')]
    pc = T('Game|GetPlayerController'); unp = T('Pawn|UnPossess'); pos = T('Pawn|Possess')
    m_call = T('|M_Swap')
    if not (len(s_ev) == len(m_ev) == len(spawn) == len(pos) == 1):
        return "SKIP counts S=%d M=%d spawn=%d possess=%d" % (len(s_ev), len(m_ev), len(spawn), len(pos))
    s_ev, m_ev, spawn, pos = s_ev[0], m_ev[0], spawn[0], pos[0]
    sp = spawn['node']['refPath']; po = pos['node']['refPath']
    # S_Swap -> spawn directly (drop the multicast hop)
    for x in m_call: call('delete_node', {'node': x['node']})
    call('delete_node', {'node': m_ev['node']})
    connect(pin(s_ev['node']['refPath'], 'then', 'out'), pin(sp, 'execute', 'in'))
    # spawn -> possess (Possess already unpossesses; removing UnPossess keeps GetController valid)
    for x in unp: call('delete_node', {'node': x['node']})
    connect(pin(sp, 'then', 'out'), pin(po, 'execute', 'in'))
    # player controller 0 -> this pawn's own controller; spawn at this pawn's location
    loc = [x for x in ii if x['type_id'] == 'Transformation|GetActorLocation' and any(c['node']['refPath'] in [p_['node']['refPath'] for p_ in pc] for c in (pin(x['node']['refPath'], 'self', 'in').get('connected_pins') or []))]
    for x in pc: call('delete_node', {'node': x['node']})
    p = pos['position']
    gc = node(EG, 'Pawn|GetController', p['x'] - 250, p['y'] + 150)
    connect(pin(gc, 'ReturnValue', 'out'), pin(po, 'self', 'in'))
    r = compile_bp(BP)
    return "ok (GetActorLocation now on self: %d) compile=%s" % (len(loc), r)
for n in ('CBP_PC_GolKosh', 'CBP_PC_Hope'):
    try: out.append(n + ": " + fix(n))
    except Exception as e: out.append(n + ": ERR " + str(e)[:600])
    try: out.append(str(call('read_graph_dsl', {'graph': {'refPath': '/Game/ThirdPerson/Blueprints/%s.%s:EventGraph' % (n, n)}})).split('(event Custom|S_Swap')[1][:900])
    except Exception as e: out.append("dsl " + str(e)[:200])
print("\n".join(out))
