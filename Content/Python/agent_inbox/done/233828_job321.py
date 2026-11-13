import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
H = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope'
G = H + ':Get Teleport Trace'
try: out.append("=== nodes\n" + dumpnodes(G))
except Exception as e: out.append("dump err " + str(e)[:300])
for t in ['Collision|CapsuleTraceByChannel', 'Collision|SphereTraceByChannel', 'Collision|BreakHitResult', 'Components|Capsule|GetScaledCapsuleRadius', 'Components|Capsule|GetScaledCapsuleHalfHeight', 'Variables|Character|GetCapsuleComponent', 'Math|Float|Max(Float)', 'Math|Vector|vector*float', 'Math|Vector|Normalize']:
    try:
        r = tpins(G, t)
        out.append("PINS %s in=%s out=%s" % (t, [(x['name'], x.get('type_id', x.get('type'))) for x in r['input_pins']], [(x['name'], x.get('type_id', x.get('type'))) for x in r['output_pins']]))
    except Exception as e: out.append("PINS %s err %s" % (t, str(e)[:200]))
for f in ['Capsule', 'MaxFloat', 'Max(', 'vector*']:
    try: out.append("TYPES %s: %s" % (f, [c.get('type_id') if isinstance(c, dict) else c for c in types(G, f)][:40]))
    except Exception as e: out.append("TYPES err " + str(e)[:200])
# callers
for g in ['EventGraph', 'Get Display Destination', 'Set Display Rotation', 'Teleport Player']:
    d = str(call('read_graph_dsl', {'graph': {'refPath': H + ':' + g}}))
    if 'GetTeleportTrace' in d or 'TeleportTrace' in d:
        out.append("=== uses in %s" % g)
        for line in d.split('\n'):
            if 'TeleportTrace' in line: out.append("   " + line.strip()[:400])
try: out.append("=== DSL DOCS\n" + str(call('get_graph_dsl_docs', {}))[:9000])
except Exception as e: out.append("docs err " + str(e)[:300])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump321.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
