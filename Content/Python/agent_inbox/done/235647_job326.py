import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
def done():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump326.txt", "w", encoding="utf-8").write("\n".join(out))
H = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope'
NEW = H + ':GetTeleportTraceCapsule'
B18 = lambda p, named: "(" + " ".join(named.get(i, "%s%d" % (p, i)) for i in range(18)) + ")"
CODE = '''(fn GetTeleportTraceCapsule ()
  ; 1) thin aim trace from the camera
  (bind cam (Game|GetPlayerCameraManager 0))
  (bind start (Transformation|GetActorLocation cam))
  (bind aimEnd (+ start (* (Transformation|GetActorForwardVector cam) (Variables|Teleport|GetTeleportRange))))
  (bind r (Variables|Default|GetCapsuleRadius))
  (bind hh (Variables|Default|GetCapsuleHalfHeight))
  (bind (aimHit aimOk) (Collision|SphereTraceByChannel start aimEnd 5.0))
  (bind %s (Collision|BreakHitResult aimHit))
  ; 2) the capsule centre for that spot: off the surface by radius+2; on floors raised, on ceilings lowered
  (bind nz (select aimOk (.z aN) 0.0))
  (bind hitC (+ (+ aLoc (* aN (+ r 2.0))) (Math|Vector|MakeVector 0.0 0.0 (* nz (- hh r)))))
  (bind c (select aimOk hitC aimEnd))
  ; 3) settle it straight down onto what is under it (walls / open air), never along the view line
  (bind raise (* hh (- 1.0 (Math|Float|Max(Float) nz (- nz)))))
  (bind (s1Hit s1Ok) (Collision|CapsuleTraceByChannel (+ c (Math|Vector|MakeVector 0.0 0.0 raise)) c r hh))
  (bind %s (Collision|BreakHitResult s1Hit))
  (if s1Ok
    (if sInit
      ; does not fit (corner, too tight): keep the last good spot unless it fits right there
      (bind (s2Hit s2Ok) (Collision|CapsuleTraceByChannel c c r hh))
      (if (not s2Ok)
        (Variables|Teleport|SetTeleportTrace c))
      (else
        (Variables|Teleport|SetTeleportTrace sLoc)))
    (else
      (Variables|Teleport|SetTeleportTrace c))))''' % (B18("a", {4: "aLoc", 6: "aN"}), B18("s", {1: "sInit", 4: "sLoc"}))
# old trace settings to copy
OLD = H + ':Get Teleport Trace'
copy = {}
for pn in ('TraceChannel', 'bTraceComplex', 'bIgnoreSelf'):
    try: copy[pn] = call('get_pin_value', {'pin': pin(OLD + '.K2Node_CallFunction_3', pn, 'in')['pin_id']})
    except Exception as e: out.append("pinval err " + str(e)[:200])
# clear the previous body (keep the entry), write the new one
for r in nodes(NEW):
    if 'FunctionEntry' not in r:
        call('delete_node', {'node': {'refPath': r}})
try: call('write_graph_dsl', {'graph': {'refPath': NEW}, 'code': CODE})
except Exception as e: out.append("WRITE FAIL " + str(e)[:1500]); done(); raise SystemExit
for x in infos(nodes(NEW)):
    if 'TraceByChannel' in x['type_id']:
        for p in x['input_pins']:
            if p['name'] in copy and copy[p['name']] not in (None, ''):
                setv(p, copy[p['name']])
try: call('arrange_nodes', {'nodes': [{'refPath': r} for r in nodes(NEW)]})
except Exception as e: out.append("arrange err " + str(e)[:200])
try: compile_bp(H); out.append("compile OK")
except Exception as e: out.append("compile FAIL " + str(e)[:800])
out.append(str(call('read_graph_dsl', {'graph': {'refPath': NEW}})))
out.append(dumpnodes(NEW))
done(); print("ok")
