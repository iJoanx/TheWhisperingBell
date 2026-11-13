import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal, inspect
from editor_toolset.toolsets.blueprint import BlueprintTools as BT
out = []
def done():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump322.txt", "w", encoding="utf-8").write("\n".join(out))
H = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope'
OLD = H + ':Get Teleport Trace'
try:
    out.append("add_variable sig: " + str(inspect.signature(BT.add_variable)))
    out.append("set_variable_instance_editable sig: " + str(inspect.signature(BT.set_variable_instance_editable)))
    out.append("set_variable_category sig: " + str(inspect.signature(BT.set_variable_category)))
    out.append("add_function_graph sig: " + str(inspect.signature(BT.add_function_graph)))
except Exception as e: out.append("sig err " + str(e)[:300])
# trace settings of the old aim trace, to copy
old_tr = OLD + '.K2Node_CallFunction_3'
copy = {}
for pn in ('TraceChannel', 'bTraceComplex', 'bIgnoreSelf'):
    try:
        p = pin(old_tr, pn, 'in'); copy[pn] = call('get_pin_value', {'pin': p['pin_id']})
    except Exception as e: out.append("pinval err %s %s" % (pn, str(e)[:200]))
out.append("old trace settings: " + str(copy))
CODE = '''(fn GetTeleportTraceCapsule ()
  ; 1) thin aim trace from the camera (same as the old version)
  (bind cam (Game|GetPlayerCameraManager 0))
  (bind start (Transformation|GetActorLocation cam))
  (bind aimEnd (+ start (* (Transformation|GetActorForwardVector cam) (Variables|Teleport|GetTeleportRange))))
  (bind r (Variables|Default|GetCapsuleRadius))
  (bind hh (Variables|Default|GetCapsuleHalfHeight))
  (bind (aimHit aimOk) (Collision|SphereTraceByChannel start aimEnd 5.0))
  (bind (a1 a2 a3 a4 aLoc a6 aN a8 a9 a10 a11 a12 a13 a14 a15 a16 a17 a18) (Collision|BreakHitResult aimHit))
  ; 2) where the capsule centre should go: off the surface by radius+2, raised by the half height on floors
  (bind up (Math|Float|Max(Float) (.z aN) 0.0))
  (bind hitTarget (+ (+ aLoc (* aN (+ r 2.0))) (Math|Vector|MakeVector 0.0 0.0 (* up (- hh r)))))
  (bind target (select aimOk hitTarget aimEnd))
  ; 3) sweep the real capsule there; a sweep always stops before touching, so corners can't trap it
  (bind (sweepHit sweepOk) (Collision|CapsuleTraceByChannel start target r hh))
  (bind (s1 sInit s3 s4 sLoc s6 s7 s8 s9 s10 s11 s12 s13 s14 s15 s16 s17 s18) (Collision|BreakHitResult sweepHit))
  (if sInit
    ; camera started inside something: sweep from the character instead
    (bind (backHit backOk) (Collision|CapsuleTraceByChannel (Transformation|GetActorLocation) target r hh))
    (bind (b1 b2 b3 b4 bLoc b6 b7 b8 b9 b10 b11 b12 b13 b14 b15 b16 b17 b18) (Collision|BreakHitResult backHit))
    (Variables|Teleport|SetTeleportTrace (select backOk bLoc target))
    (else
      (Variables|Teleport|SetTeleportTrace (select sweepOk sLoc target)))))'''
try:
    g = call('add_function_graph', {'blueprint': {'refPath': H}, 'graph_name': 'GetTeleportTraceCapsule'})['refPath']
    out.append("graph " + g)
    call('write_graph_dsl', {'graph': {'refPath': g}, 'code': CODE})
except Exception as e:
    out.append("WRITE FAIL " + str(e)[:1500]); done(); raise SystemExit
# copy channel/complex onto the new traces
for x in infos(nodes(g)):
    if 'TraceByChannel' in x['type_id']:
        for p in x['input_pins']:
            if p['name'] in copy and copy[p['name']] not in (None, ''):
                try: setv(p, copy[p['name']])
                except Exception as e: out.append("setv err " + str(e)[:200])
try: call('arrange_nodes', {'graph': {'refPath': g}})
except Exception as e: out.append("arrange err " + str(e)[:200])
try: compile_bp(H); out.append("compile OK")
except Exception as e: out.append("compile FAIL " + str(e)[:800])
out.append("=== new fn\n" + str(call('read_graph_dsl', {'graph': {'refPath': g}})))
out.append("=== nodes\n" + dumpnodes(g))
done(); print("ok")
